from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from core.exceptions import register_exception_handlers
from routers.user import auth_router, users_router
from routers import order, product, health
from contextlib import asynccontextmanager
from middleware.timing import RequestTimingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from middleware.logging import LoggingMiddleware
from core.logging import setup_logging, get_logger
from cache.redis_client import redis_client
from models.base import engine
from config import get_settings
from prometheus_fastapi_instrumentator import Instrumentator

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    setup_logging()
    logger.info(
        "application_starting", environment=settings.environment, app=settings.app_name
    )

    # DB connectivity check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    # Redis connectivity check
    try:
        await redis_client.ping()
        logger.info("redis_connected")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e))
        raise

    logger.info("application_ready")
    yield  # app serves traffic here

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("application_shutting_down")
    await engine.dispose()
    logger.info("database_pool_closed")
    await redis_client.aclose()
    logger.info("redis_connection_closed")
    logger.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Marketo — production-grade e-commerce API",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Observability ──────────────────────────────────────────────────────────
if settings.enable_metrics:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Middleware (applied in reverse order — last added = first executed) ────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestTimingMiddleware)

# ── Exception handlers ─────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Routers ────────────────────────────────────────────────────────────────
# Public routes
app.include_router(health.router)
# /v1 prefixed routes
app.include_router(auth_router, prefix="/v1")  # /v1/auth/register, /v1/auth/login
app.include_router(users_router, prefix="/v1")  # /v1/users/me, /v1/users/ (admin)
app.include_router(product.router, prefix="/v1")  # /v1/products/
app.include_router(order.router, prefix="/v1")  # /v1/orders/
