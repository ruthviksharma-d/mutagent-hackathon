"""Simple health-check endpoint used by the dashboard, extension, and CI."""
from fastapi import APIRouter

from config.settings import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
