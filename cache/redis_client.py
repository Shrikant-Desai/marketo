# cache/redis_client.py
import redis.asyncio as redis
from core.config import get_settings

settings = get_settings()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

async def get_cache(key: str) -> str | None:
    return await redis_client.get(key)

async def set_cache(key: str, value: str, ttl: int) -> None:
    await redis_client.set(key, value, ex=ttl)

async def delete_cache(key: str) -> None:
    await redis_client.delete(key)

async def delete_pattern(pattern: str) -> None:
    keys = await redis_client.keys(pattern)
    if keys:
        await redis_client.delete(*keys)
