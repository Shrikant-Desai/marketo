from fastapi import APIRouter
from core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment
    }
