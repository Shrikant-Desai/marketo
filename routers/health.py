# routers/health.py
import time
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from auth.dependencies import get_db
from cache.redis_client import redis_client
from config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", summary="Liveness probe")
async def health_check():
    """Always returns 200 — confirms the process is alive. No DB/Redis hit."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "timestamp": time.time(),
    }


@router.get("/health/ready", summary="Readiness probe")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Checks DB and Redis connectivity.
    Returns 200 if all healthy, 503 if any dependency is down.
    Kubernetes / load balancers use this to route traffic.
    """
    checks: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_healthy else 503,
        content={
            "status": "ready" if all_healthy else "degraded",
            "checks": checks,
        },
    )
