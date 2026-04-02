import json
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.product import ProductCreate, ProductUpdate
from repositories.product_repository import ProductRepository
from cache.redis_client import get_cache, set_cache, delete_cache, delete_pattern
from core.logging import get_logger

logger = get_logger(__name__)

_PRODUCT_CACHE_TTL = 3600  # 1 hour for individual products
_LIST_CACHE_TTL = 300  # 5 minutes for listing


async def get_all_products(skip: int, limit: int, db: AsyncSession):
    cache_key = f"products:list:{skip}:{limit}"
    logger.debug("product_service.get_all", skip=skip, limit=limit)

    cached = await get_cache(cache_key)
    if cached:
        logger.debug("product_service.cache_hit", key=cache_key)
        return json.loads(cached)

    logger.debug("product_service.cache_miss", key=cache_key)
    repo = ProductRepository(db)
    products = await repo.find_all(skip=skip, limit=limit)
    await set_cache(
        cache_key, json.dumps(jsonable_encoder(products)), ttl=_LIST_CACHE_TTL
    )
    logger.info("product_service.get_all_complete", count=len(products))
    return products


async def get_product_by_id(product_id: int, db: AsyncSession):
    cache_key = f"product:{product_id}"
    logger.debug("product_service.get_by_id", product_id=product_id)

    cached = await get_cache(cache_key)
    if cached:
        logger.debug("product_service.cache_hit", key=cache_key)
        return json.loads(cached)

    repo = ProductRepository(db)
    product = await repo.find_by_id(product_id)
    if not product:
        logger.warning("product_service.not_found", product_id=product_id)
        raise HTTPException(status_code=404, detail="Product not found")

    await set_cache(
        cache_key, json.dumps(jsonable_encoder(product)), ttl=_PRODUCT_CACHE_TTL
    )
    return product


async def search_products(q: str, db: AsyncSession):
    logger.info("product_service.search", q=q)
    repo = ProductRepository(db)
    results = await repo.search(q)
    logger.info("product_service.search_results", q=q, count=len(results))
    return results


async def create_product(product_in: ProductCreate, seller_id: int, db: AsyncSession):
    logger.info(
        "product_service.create",
        sku=product_in.sku,
        name=product_in.name,
        seller_id=seller_id,
    )
    repo = ProductRepository(db)
    data = product_in.model_dump()
    data["seller_id"] = seller_id
    product = await repo.create(data)
    await delete_pattern("products:list:*")  # invalidate all list caches
    logger.info("product_service.created", product_id=product.id, sku=product.sku)
    return product


async def update_product(
    product_id: int, product_in: ProductUpdate, seller_id: int, db: AsyncSession
):
    """Update a product. Only the seller who owns it (or an admin) may do this.
    Ownership is verified here; callers must pass the current user's id as seller_id.
    Admins bypass the ownership check — that distinction is enforced in the router.
    """
    logger.info("product_service.update", product_id=product_id, seller_id=seller_id)
    repo = ProductRepository(db)
    product = await repo.find_by_id(product_id)
    if not product or not product.is_active:
        logger.warning("product_service.update_not_found", product_id=product_id)
        raise HTTPException(status_code=404, detail="Product not found")

    if product.seller_id != seller_id:
        logger.warning(
            "product_service.update_forbidden",
            product_id=product_id,
            seller_id=seller_id,
            actual_seller=product.seller_id,
        )
        raise HTTPException(
            status_code=403, detail="You can only update your own products"
        )

    update_data = product_in.model_dump(exclude_none=True)
    product = await repo.update(product, update_data)

    await delete_cache(f"product:{product_id}")
    await delete_pattern("products:list:*")
    logger.info("product_service.update_complete", product_id=product_id)
    return product


async def delete_product(product_id: int, seller_id: int, db: AsyncSession) -> None:
    logger.info("product_service.delete", product_id=product_id, seller_id=seller_id)
    repo = ProductRepository(db)
    product = await repo.find_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.seller_id != seller_id:
        logger.warning(
            "product_service.delete_forbidden",
            product_id=product_id,
            seller_id=seller_id,
            actual_seller=product.seller_id,
        )
        raise HTTPException(
            status_code=403, detail="You can only delete your own products"
        )

    await repo.delete(product)  # soft delete
    await delete_cache(f"product:{product_id}")
    await delete_pattern("products:list:*")
    logger.info("product_service.deleted", product_id=product_id)
