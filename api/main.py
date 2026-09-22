"""
Viora – FastAPI Application.
Serves the webhook endpoint for Exotel, the dashboard API,
and the WebSocket feed for the admin dashboard.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import admin, appointments, dashboard, webhooks
from config.settings import get_settings
from db.session import create_all_tables

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Viora API starting up (env=%s, hms=%s)", settings.ENVIRONMENT, settings.HMS_PROVIDER)
    try:
        await create_all_tables()
    except Exception as e:
        logger.warning("Database connection failed. Proceeding in limited mode: %s", e)
    yield
    logger.info("Viora API shutting down.")


app = FastAPI(
    title="Viora – Healthcare Voice Receptionist API",
    description=(
        "Backend API for Viora: AI voice receptionist for clinics and hospitals. "
        "Handles appointment booking, call management, dashboard data, and Exotel webhook processing."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ────────────────────────────────────────────────────────────────────
app.include_router(webhooks.router, prefix="/webhooks", tags=["Telephony Webhooks"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Admin Dashboard"])
app.include_router(admin.router, prefix="/admin", tags=["Admin Settings"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])


# ─── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health() -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "hms": settings.HMS_PROVIDER.value,
        "gemini": "ready" if settings.gemini_ready else "demo_mode",
        "sarvam": "ready" if settings.sarvam_ready else "demo_mode",
        "livekit": "ready" if settings.livekit_ready else "not_configured",
    })


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"message": "Viora API is running.", "docs": "/docs"})
