# repositories/user_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
import structlog

logger = structlog.get_logger(__name__)


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_id(self, user_id: int) -> User | None:
        logger.debug("user_repo.find_by_id", user_id=user_id)
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        logger.debug("user_repo.find_by_email", email=email)
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def find_by_username(self, username: str) -> User | None:
        logger.debug("user_repo.find_by_username", username=username)
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def find_all(self, skip: int = 0, limit: int = 20) -> list[User]:
        logger.debug("user_repo.find_all", skip=skip, limit=limit)
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, data: dict) -> User:
        logger.debug("user_repo.create", username=data.get("username"))
        user = User(**data)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        logger.info("user_repo.created", user_id=user.id, username=user.username)
        return user

    async def update(self, user: User, data: dict) -> User:
        logger.debug("user_repo.update", user_id=user.id, fields=list(data.keys()))
        for key, value in data.items():
            setattr(user, key, value)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        logger.debug("user_repo.delete", user_id=user.id)
        await self.db.delete(user)
        await self.db.flush()
        logger.info("user_repo.deleted", user_id=user.id)
