from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from schemas.orders import OrderCreate, OrderResponse
from core.dependencies import get_db, get_current_user
import services.orders as order_service

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await order_service.create_order(order, current_user["id"], db)

@router.get("/my-orders", response_model=List[OrderResponse])
async def get_my_orders(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    return await order_service.get_orders_by_user(current_user["id"], db)
