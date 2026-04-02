from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.user import RegisterRequest, LoginRequest, TokenResponse, RegisterResponse
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from repositories.user_repository import UserRepository
from tasks.email_tasks import send_welcome_email
from core.logging import get_logger

logger = get_logger(__name__)


async def register_user(data: RegisterRequest, db: AsyncSession) -> RegisterResponse:
    logger.info("user_service.register_start", username=data.username, email=data.email)
    repo = UserRepository(db)

    if await repo.find_by_email(data.email):
        logger.warning(
            "user_service.register_conflict", reason="email_taken", email=data.email
        )
        raise HTTPException(status_code=409, detail="Email already registered")
    if await repo.find_by_username(data.username):
        logger.warning(
            "user_service.register_conflict",
            reason="username_taken",
            username=data.username,
        )
        raise HTTPException(status_code=409, detail="Username already taken")

    user_data = data.model_dump()
    user_data["password"] = hash_password(user_data.pop("password"))
    user = await repo.create(user_data)

    # Send welcome email as async background task — don't block the response
    send_welcome_email.delay(user.email, user.username)
    logger.info(
        "user_service.register_complete", user_id=user.id, username=user.username
    )

    return RegisterResponse(
        msg="Registration successful",
        id=user.id,
        username=user.username,
        email=user.email,
    )


async def login_user(data: LoginRequest, db: AsyncSession) -> TokenResponse:
    logger.info("user_service.login_attempt", login=data.login)
    repo = UserRepository(db)

    # Support login by email or username
    user = await repo.find_by_email(data.login) or await repo.find_by_username(
        data.login
    )

    if not user:
        logger.warning(
            "user_service.login_failed", reason="user_not_found", login=data.login
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user.password):
        logger.warning(
            "user_service.login_failed", reason="wrong_password", user_id=user.id
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        logger.warning("user_service.login_blocked", reason="inactive", user_id=user.id)
        raise HTTPException(status_code=403, detail="Account is deactivated")

    token_data = {"sub": user.email, "id": user.id, "role": user.role}
    logger.info("user_service.login_success", user_id=user.id, role=user.role)
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


async def get_user_by_id(user_id: int, db: AsyncSession):
    logger.debug("user_service.get_user", user_id=user_id)
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        logger.warning("user_service.get_user_not_found", user_id=user_id)
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def list_users(skip: int, limit: int, db: AsyncSession) -> list:
    logger.debug("user_service.list_users", skip=skip, limit=limit)
    repo = UserRepository(db)
    return await repo.find_all(skip=skip, limit=limit)


async def update_user(user_id: int, data: dict, db: AsyncSession):
    logger.info("user_service.update_user", user_id=user_id, fields=list(data.keys()))
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent duplicate email/username takeover
    update_data = {k: v for k, v in data.items() if v is not None}
    if "email" in update_data:
        conflict = await repo.find_by_email(update_data["email"])
        if conflict and conflict.id != user_id:
            raise HTTPException(status_code=409, detail="Email already in use")
    if "username" in update_data:
        conflict = await repo.find_by_username(update_data["username"])
        if conflict and conflict.id != user_id:
            raise HTTPException(status_code=409, detail="Username already taken")

    updated = await repo.update(user, update_data)
    logger.info("user_service.update_complete", user_id=user_id)
    return updated


async def delete_user(user_id: int, db: AsyncSession) -> None:
    logger.info("user_service.delete_user", user_id=user_id)
    repo = UserRepository(db)
    user = await repo.find_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await repo.delete(user)
    logger.info("user_service.delete_complete", user_id=user_id)


# create_user alias for backward compat
async def create_user(user_in, db):
    from schemas.user import RegisterRequest

    reg = RegisterRequest(
        email=user_in.email,
        username=user_in.username,
        password=user_in.password,
    )
    from services.user_service import register_user

    return await register_user(reg, db)
