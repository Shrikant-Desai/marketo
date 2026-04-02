from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.product import ProductCreate, ProductUpdate, ProductResponse
from auth.dependencies import get_db, get_current_user
import services.product_service as product_service

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "/", response_model=list[ProductResponse], summary="List all active products"
)
async def get_products(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),  # protected
):
    return await product_service.get_all_products(skip, limit, db)


@router.get(
    "/search",
    response_model=list[ProductResponse],
    summary="Full-text search for products",
)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),  # protected
):
    return await product_service.search_products(q, db)


@router.get(
    "/{product_id}", response_model=ProductResponse, summary="Get product by ID"
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),  # protected
):
    return await product_service.get_product_by_id(product_id, db)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (sellers only)",
)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await product_service.create_product(product, current_user["id"], db)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product (seller or admin)",
)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return await product_service.update_product(product_id, product, db)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a product (owner only)",
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await product_service.delete_product(product_id, current_user["id"], db)
