# services/order_service.py
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.orders_repository import OrderRepository
from repositories.products_repository import ProductRepository
from repositories.users_repository import UserRepository
from schemas.orders import OrderCreate
from models.orders import Order
from cache.redis_client import delete_pattern
from tasks.email_tasks import send_order_confirmation
from core.logging import get_logger

logger = get_logger(__name__)


async def create_order(data: OrderCreate, buyer_id: int, db: AsyncSession) -> Order:
    logger.info(
        "order_service.create_start",
        buyer_id=buyer_id,
        item_count=len(data.items),
    )
    product_repo = ProductRepository(db)
    order_repo = OrderRepository(db)

    # 1. Load all products in one query — avoid N+1
    product_ids = [item.product_id for item in data.items]
    products = await product_repo.find_by_ids(product_ids)
    product_map = {p.id: p for p in products}
    logger.debug(
        "order_service.products_loaded", found=len(products), requested=len(product_ids)
    )

    # 2. Validate every item
    for item in data.items:
        product = product_map.get(item.product_id)
        if not product:
            logger.warning("order_service.product_missing", product_id=item.product_id)
            raise HTTPException(404, f"Product {item.product_id} not found")
        if not product.is_active:
            logger.warning(
                "order_service.product_inactive",
                product_id=item.product_id,
                name=product.name,
            )
            raise HTTPException(422, f"Product '{product.name}' is no longer available")
        if product.stock < item.quantity:
            logger.warning(
                "order_service.insufficient_stock",
                product_id=item.product_id,
                requested=item.quantity,
                available=product.stock,
            )
            raise HTTPException(
                422, f"Only {product.stock} unit(s) of '{product.name}' in stock"
            )

    # 3. Calculate total — always use DB price, never trust client data
    total = round(
        sum(product_map[i.product_id].price * i.quantity for i in data.items), 2
    )
    logger.debug("order_service.total_calculated", total=total)

    # 4. Create order + line items + decrement stock — all in one transaction
    order = await order_repo.create(
        buyer_id=buyer_id,
        total=total,
        items=[
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": product_map[item.product_id].price,
            }
            for item in data.items
        ],
    )

    for item in data.items:
        await product_repo.decrement_stock(item.product_id, item.quantity)

    # 5. Invalidate product list cache — stock counts changed
    await delete_pattern("product:*")
    await delete_pattern("products:list:*")

    # 6. Send confirmation email asynchronously — don't block the response
    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(buyer_id)
    if user:
        send_order_confirmation.delay(
            user_email=user.email,
            username=user.username,
            order_id=order.id,
            total=total,
        )

    logger.info("order_service.create_complete", order_id=order.id, total=total)
    return order


async def get_order(order_id: int, buyer_id: int, db: AsyncSession) -> Order:
    logger.debug("order_service.get", order_id=order_id, buyer_id=buyer_id)
    order_repo = OrderRepository(db)
    order = await order_repo.find_by_id(order_id)
    if not order:
        logger.warning("order_service.not_found", order_id=order_id)
        raise HTTPException(404, "Order not found")
    if order.buyer_id != buyer_id:
        logger.warning(
            "order_service.access_denied",
            order_id=order_id,
            requester=buyer_id,
            owner=order.buyer_id,
        )
        raise HTTPException(403, "Not your order")
    return order


async def get_my_orders(buyer_id: int, db: AsyncSession) -> list[Order]:
    logger.debug("order_service.get_my_orders", buyer_id=buyer_id)
    order_repo = OrderRepository(db)
    orders = await order_repo.find_by_buyer(buyer_id)
    logger.info(
        "order_service.get_my_orders_complete", buyer_id=buyer_id, count=len(orders)
    )
    return orders


async def cancel_order(order_id: int, buyer_id: int, db: AsyncSession) -> Order:
    logger.info("order_service.cancel_start", order_id=order_id, buyer_id=buyer_id)
    order = await get_order(order_id, buyer_id, db)

    if order.status != "pending":
        logger.warning(
            "order_service.cancel_invalid_status",
            order_id=order_id,
            current_status=order.status,
        )
        raise HTTPException(422, f"Cannot cancel a '{order.status}' order")

    product_repo = ProductRepository(db)
    # Restore stock for every cancelled item
    for item in order.items:
        await product_repo.increment_stock(item.product_id, item.quantity)
        logger.debug(
            "order_service.stock_restored",
            product_id=item.product_id,
            quantity=item.quantity,
        )

    order_repo = OrderRepository(db)
    order = await order_repo.update_status(order_id, "cancelled")
    await delete_pattern("product:*")
    await delete_pattern("products:list:*")
    logger.info("order_service.cancelled", order_id=order_id)
    return order
