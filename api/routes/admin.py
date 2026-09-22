"""Viora – Admin API for settings and feature flags."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.middleware.auth import require_dashboard_key
from config.settings import get_settings

router = APIRouter(dependencies=[Depends(require_dashboard_key)])
settings = get_settings()

# In-memory feature flags (persisted via settings / env in production)
_feature_flags: dict[str, bool] = {
    "triage_enabled": True,
    "lab_lookup_enabled": True,
    "prescription_lookup_enabled": True,
    "registration_enabled": True,
    "faq_enabled": True,
    "sms_summary_enabled": False,  # requires Exotel config
}


@router.get("/flags")
async def get_flags() -> dict:
    return {"flags": _feature_flags}


@router.patch("/flags/{flag_name}")
async def toggle_flag(flag_name: str, enabled: bool) -> dict:
    if flag_name not in _feature_flags:
        return JSONResponse(status_code=404, content={"error": f"Flag '{flag_name}' not found."})
    _feature_flags[flag_name] = enabled
    return {"flag": flag_name, "enabled": enabled}


@router.get("/config")
async def get_config() -> dict:
    """Return non-sensitive runtime config for the dashboard settings page."""
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "hms_provider": settings.HMS_PROVIDER.value,
        "supported_languages": settings.SUPPORTED_LANGUAGES,
        "gemini_model": settings.GEMINI_MODEL,
        "sarvam_tts_model": settings.SARVAM_TTS_MODEL,
        "gemini_ready": settings.gemini_ready,
        "sarvam_ready": settings.sarvam_ready,
        "livekit_ready": settings.livekit_ready,
        "exotel_ready": settings.exotel_ready,
        "audio_retention_days": settings.AUDIO_RETENTION_DAYS,
        "transcript_retention_days": settings.TRANSCRIPT_RETENTION_DAYS,
    }


@router.post("/simulator/token")
async def get_simulator_token(room_name: str = "viora-demo", identity: str = "admin") -> dict:
    """
    Generate a LiveKit access token for the browser-based Call Simulator.
    The browser uses this token to join a LiveKit room where Viora picks up.
    """
    from livekit.api import AccessToken, VideoGrants
    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name("Admin (Simulator)")
        .with_grants(VideoGrants(room_join=True, room=room_name))
    )
    return {
        "token": token.to_jwt(),
        "room": room_name,
        "livekit_url": settings.LIVEKIT_URL,
    }
