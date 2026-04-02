from sqlalchemy.ext.asyncio import AsyncSession
from models.order import Order
from repositories.base import BaseRepository

class OrderRepository(BaseRepository[Order]):
    def __init__(self):
        super().__init__(Order)

order_repo = OrderRepository()
