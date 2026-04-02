from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.user import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RegisterResponse,
    UserResponse,
    UserUpdate,
    UserRoleUpdate,
)
from auth.dependencies import get_db, get_current_user, require_admin
import services.user_service as user_service

# ── Auth router (public) ───────────────────────────────────────────────────
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account (role: 'user' or 'seller')",
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Public — no token required. Role defaults to 'user'; may self-select 'seller'."""
    return await user_service.register_user(data, db)


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email or username to get JWT tokens",
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Public — no token required."""
    return await user_service.login_user(data, db)


# ── Users router (protected) ──────────────────────────────────────────────
users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await user_service.get_user_by_id(current_user["id"], db)


@users_router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # exclude_none=True so unset optional fields are not sent to the service
    return await user_service.update_user(current_user["id"], data.model_dump(exclude_none=True), db)


@users_router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete current user account",
)
async def delete_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    await user_service.delete_user(current_user["id"], db)


@users_router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
)
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    return await user_service.list_users(skip=skip, limit=limit, db=db)


@users_router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update a user's role (admin only)",
)
async def update_role(
    user_id: int,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_admin),
):
    """Admin-only. Allows promoting to 'seller', 'admin', or demoting to 'user'."""
    return await user_service.update_user_role(user_id, data.role, db)
