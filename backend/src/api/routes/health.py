"""Health check endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...schemas.response import HealthResponse
from ...config.settings import settings
from ..dependencies import get_db_session

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db_session)) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns service status, version, and database connectivity.
    """
    # Check database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        database=db_status
    )


@router.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
