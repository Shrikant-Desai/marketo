from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.orders import OrderCreate, OrderResponse
from auth.dependencies import get_db, get_current_user
import services.orders_service as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order (multi-item)",
)
async def create_order(
    order: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await order_service.create_order(order, current_user["id"], db)


@router.get(
    "/my",
    response_model=list[OrderResponse],
    summary="Get all orders for the current user",
)
async def get_my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await order_service.get_my_orders(current_user["id"], db)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get a specific order (owner only)",
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await order_service.get_order(order_id, current_user["id"], db)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Cancel a pending order and restore stock",
)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await order_service.cancel_order(order_id, current_user["id"], db)
