from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.order import OrderCreate, OrderResponse
from auth.dependencies import get_db, get_current_user
import services.order_service as order_service
from tasks.email_tasks import send_order_confirmation

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order (multi-item)",
)
async def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    order_obj, user_email, username, total = await order_service.create_order(
        order, current_user["id"], db
    )
    # Dispatch AFTER the service returns so the DB session commit
    # (which happens in get_db after this route exits) has already
    # persisted the order before Celery picks up the task.
    if user_email:
        background_tasks.add_task(
            send_order_confirmation.delay,
            user_email=user_email,
            username=username,
            order_id=order_obj.id,
            total=total,
        )
    return order_obj


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
