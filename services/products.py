from sqlalchemy.ext.asyncio import AsyncSession
from schemas.products import ProductCreate
from repositories.products import product_repo
from core.exceptions import AppException

async def create_product(product_in: ProductCreate, seller_id: int, db: AsyncSession):
    product_data = product_in.model_dump()
    product_data["seller_id"] = seller_id
    return await product_repo.create(db, product_data)

async def get_all_products(skip: int, limit: int, db: AsyncSession):
    return await product_repo.get_all(db, skip=skip, limit=limit)

async def get_product_by_id(product_id: int, db: AsyncSession):
    product = await product_repo.get_by_id(db, product_id)
    if not product:
        raise AppException("Product not found", status_code=404)
    return product
