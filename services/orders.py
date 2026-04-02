from sqlalchemy.ext.asyncio import AsyncSession
from schemas.orders import OrderCreate
from repositories.orders import order_repo
from repositories.products import product_repo
from core.exceptions import AppException

async def create_order(order_in: OrderCreate, user_id: int, db: AsyncSession):
    product = await product_repo.get_by_id(db, order_in.product_id)
    if not product:
        raise AppException("Product not found", status_code=404)
    if product.stock < order_in.quantity:
        raise AppException("Insufficient stock")

    order_data = order_in.model_dump()
    order_data["user_id"] = user_id
    order_data["total_price"] = product.price * order_in.quantity
    order_data["status"] = "pending"

    order = await order_repo.create(db, order_data)

    # Note: Stock should ideally be updated in a structured transaction or event
    await db.refresh(product)
    product.stock -= order_in.quantity
    
    return order

async def get_orders_by_user(user_id: int, db: AsyncSession):
    # This could be more efficient with a specific repo method
    orders = await order_repo.get_all(db, limit=1000)
    return [o for o in orders if o.user_id == user_id]
