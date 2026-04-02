import json
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.order_repository import OrderRepository
from repositories.product_repository import ProductRepository
from schemas.order import OrderCreate
from models.order import Order
from cache.redis_client import delete_pattern
from tasks.email_tasks import send_order_confirmation


class OrderService:
    def __init__(self, db: AsyncSession):
        self.order_repo = OrderRepository(db)
        self.product_repo = ProductRepository(db)
        self.db = db

    async def create_order(self, data: OrderCreate, buyer_id: int) -> Order:
        # 1. Load all products in one query — never N+1 queries
        product_ids = [item.product_id for item in data.items]
        products = await self.product_repo.find_by_ids(product_ids)
        product_map = {p.id: p for p in products}

        # 2. Validate every item
        for item in data.items:
            product = product_map.get(item.product_id)
            if not product:
                raise HTTPException(404, f"Product {item.product_id} not found")
            if not product.is_active:
                raise HTTPException(
                    422, f"Product '{product.name}' is no longer available"
                )
            if product.stock < item.quantity:
                raise HTTPException(
                    422, f"Only {product.stock} units of '{product.name}' in stock"
                )

        # 3. Calculate total — use DB price, never trust client prices
        total = sum(
            product_map[item.product_id].price * item.quantity for item in data.items
        )

        # 4. Create order + decrement stock — all in one transaction
        # The get_db dependency commits on success, rolls back on failure
        order = await self.order_repo.create(
            buyer_id=buyer_id,
            total=round(total, 2),
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
            await self.product_repo.decrement_stock(item.product_id, item.quantity)

        # 5. Invalidate product cache — stock changed
        await delete_pattern("product:*")

        # 6. Trigger async tasks — respond immediately, do slow work later
        send_order_confirmation.delay(
            buyer_id=buyer_id,
            order_id=order.id,
            total=total,
        )

        return order

    async def get_order(self, order_id: int, buyer_id: int) -> Order:
        order = await self.order_repo.find_by_id(order_id)
        if not order:
            raise HTTPException(404, "Order not found")
        # Buyers can only see their own orders; admins see all
        if order.buyer_id != buyer_id:
            raise HTTPException(403, "Not your order")
        return order

    async def cancel_order(self, order_id: int, buyer_id: int) -> Order:
        order = await self.get_order(order_id, buyer_id)
        if order.status != "pending":
            raise HTTPException(422, f"Cannot cancel a {order.status} order")

        # Restore stock for each item
        for item in order.items:
            await self.product_repo.increment_stock(item.product_id, item.quantity)

        order = await self.order_repo.update_status(order_id, "cancelled")
        await delete_pattern("product:*")
        return order
