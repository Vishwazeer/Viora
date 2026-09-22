"""Viora – Dashboard authentication middleware."""
from fastapi import Header, HTTPException

from config.settings import get_settings

settings = get_settings()


async def require_dashboard_key(x_admin_key: str | None = Header(default=None)) -> None:
    """FastAPI dependency: validates the admin API key header."""
    if not x_admin_key or x_admin_key != settings.DASHBOARD_ADMIN_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Admin-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
