from sqlalchemy.ext.asyncio import AsyncSession
from core.security import verify_password, create_access_token, create_refresh_token
from core.exceptions import AppException
from schemas.auth import LoginRequest, TokenResponse
from repositories.users import user_repo

async def login(req: LoginRequest, db: AsyncSession) -> TokenResponse:
    user = await user_repo.get_by_username(db, req.username)
    if not user or not verify_password(req.password, user.password):
        raise AppException("Invalid credentials", status_code=401)
    
    if not user.is_active:
        raise AppException("User is inactive", status_code=400)

    token_data = {"sub": user.username, "id": user.id, "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data)
    )
