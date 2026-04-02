from sqlalchemy.ext.asyncio import AsyncSession
from schemas.users import UserCreate
from repositories.users import user_repo
from core.security import hash_password
from core.exceptions import AppException

async def create_user(user_in: UserCreate, db: AsyncSession):
    existing = await user_repo.get_by_username(db, user_in.username)
    if existing:
        raise AppException("Username already taken")
    existing_email = await user_repo.get_by_email(db, user_in.email)
    if existing_email:
        raise AppException("Email already registered")
    
    user_data = user_in.model_dump()
    user_data["password"] = hash_password(user_data["password"])
    
    return await user_repo.create(db, user_data)

async def get_user_by_id(user_id: int, db: AsyncSession):
    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise AppException("User not found", status_code=404)
    return user
