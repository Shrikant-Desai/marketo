from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from core.exceptions import register_exception_handlers
from routers import health, auth, users, products, orders
from contextlib import asynccontextmanager
from middleware.timing import RequestTimingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.logging import LoggingMiddleware
from core.logging import setup_logging, get_logger
from cache.redis_client import redis_client
from models.base import engine
from core.config import get_settings
from prometheus_fastapi_instrumentator import Instrumentator

settings = get_settings()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("application_starting", environment=settings.environment)

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    # Redis check
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    logger.info("application_ready")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    await engine.dispose()
    logger.info("database_pool_closed")
    await redis_client.aclose()
    logger.info("redis_connection_closed")
    logger.info("application_stopped")

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    lifespan=lifespan,
)

if settings.enable_metrics:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update for production
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestTimingMiddleware)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router, prefix="/v1")
app.include_router(users.router, prefix="/v1")
app.include_router(products.router, prefix="/v1")
app.include_router(orders.router, prefix="/v1")
