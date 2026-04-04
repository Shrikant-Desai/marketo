from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models.order import Order, OrderItem
import structlog

logger = structlog.get_logger(__name__)


class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, order_id: int) -> Order | None:
        """Load order with all its items eagerly to avoid lazy-load issues."""
        logger.debug("order_repo.find_by_id", order_id=order_id)
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def find_by_buyer(self, buyer_id: int) -> list[Order]:
        logger.debug("order_repo.find_by_buyer", buyer_id=buyer_id)
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.buyer_id == buyer_id)
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self,
        buyer_id: int,
        total: float,
        items: list[dict],  # [{product_id, quantity, unit_price}]
    ) -> Order:
        """Create an order with all its line items in a single flush."""
        logger.debug(
            "order_repo.create",
            buyer_id=buyer_id,
            total=total,
            item_count=len(items),
        )
        order = Order(buyer_id=buyer_id, total=total)
        self.db.add(order)
        await self.db.flush()  # get order.id before creating items

        for item_data in items:
            order_item = OrderItem(order_id=order.id, **item_data)
            self.db.add(order_item)

        await self.db.flush()

        # Eagerly reload to avoid MissingGreenlet on updated_at / items.
        # populate_existing=True forces SQLAlchemy to overwrite the expired
        # scalar attributes (like updated_at) and reload relationships.
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .execution_options(populate_existing=True)
            .where(Order.id == order.id)
        )
        order = result.scalar_one()

        logger.info("order_repo.created", order_id=order.id, total=total)
        return order

    async def update_status(self, order_id: int, status: str) -> Order | None:
        logger.debug("order_repo.update_status", order_id=order_id, status=status)
        order = await self.find_by_id(order_id)
        if order:
            order.status = status
            await self.db.flush()
            
            # Eagerly reload to prevent MissingGreenlet on updated_at
            result = await self.db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .execution_options(populate_existing=True)
                .where(Order.id == order_id)
            )
            order = result.scalar_one()
            
            logger.info("order_repo.status_updated", order_id=order_id, status=status)
        return order
