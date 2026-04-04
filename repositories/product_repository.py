# repositories/product_repository.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from models.product import Product
import structlog

logger = structlog.get_logger(__name__)


class ProductRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, product_id: int) -> Product | None:
        """Return an active product by PK; soft-deleted products return None."""
        logger.debug("product_repo.find_by_id", product_id=product_id)
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def find_by_sku(self, sku: str) -> Product | None:
        """Return the product with this SKU regardless of active status."""
        logger.debug("product_repo.find_by_sku", sku=sku)
        result = await self.db.execute(
            select(Product).where(Product.sku == sku)
        )
        return result.scalar_one_or_none()

    async def find_by_ids(self, ids: list[int]) -> list[Product]:
        """Bulk-load **active** products avoiding N+1 queries.

        Soft-deleted products are excluded so that order validation
        correctly surfaces the 'no longer available' error.
        """
        logger.debug("product_repo.find_by_ids", ids=ids, count=len(ids))
        result = await self.db.execute(
            select(Product).where(
                Product.id.in_(ids),
                Product.is_active == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def find_all(
        self, skip: int = 0, limit: int = 50, active_only: bool = True
    ) -> list[Product]:
        logger.debug("product_repo.find_all", skip=skip, limit=limit)
        stmt = select(Product)
        if active_only:
            stmt = stmt.where(Product.is_active == True)  # noqa: E712
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search(self, q: str) -> list[Product]:
        """PostgreSQL full-text search across name + description."""
        logger.info("product_repo.search", q=q)
        search_vector = func.to_tsvector(
            "english", Product.name + " " + func.coalesce(Product.description, "")
        )
        search_query = func.plainto_tsquery("english", q)
        stmt = (
            select(Product)
            .where(search_vector.op("@@")(search_query))
            .where(Product.is_active == True)  # noqa: E712
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: dict) -> Product:
        logger.debug("product_repo.create", sku=data.get("sku"), name=data.get("name"))
        product = Product(**data)
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        logger.info("product_repo.created", product_id=product.id, sku=product.sku)
        return product

    async def update(self, product: Product, data: dict) -> Product:
        logger.debug(
            "product_repo.update", product_id=product.id, fields=list(data.keys())
        )
        for key, value in data.items():
            setattr(product, key, value)
        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def decrement_stock(self, product_id: int, quantity: int) -> None:
        logger.debug(
            "product_repo.decrement_stock", product_id=product_id, quantity=quantity
        )
        product = await self.find_by_id(product_id)
        if product:
            product.stock -= quantity
            await self.db.flush()

    async def increment_stock(self, product_id: int, quantity: int) -> None:
        logger.debug(
            "product_repo.increment_stock", product_id=product_id, quantity=quantity
        )
        product = await self.find_by_id(product_id)
        if product:
            product.stock += quantity
            await self.db.flush()

    async def delete(self, product: Product) -> None:
        logger.debug("product_repo.soft_delete", product_id=product.id)
        product.is_active = False  # soft delete — preserve order history
        await self.db.flush()
        logger.info("product_repo.deactivated", product_id=product.id)
