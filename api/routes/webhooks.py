"""
Viora – Exotel Webhook Handler.
Receives inbound call events from Exotel and triggers the LiveKit agent.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_exotel_signature(payload: bytes, signature: str | None) -> bool:
    """Verify Exotel HMAC-SHA256 webhook signature."""
    if not settings.EXOTEL_API_TOKEN or not signature:
        return not settings.is_production  # skip verification in dev/demo
    expected = hmac.new(
        settings.EXOTEL_API_TOKEN.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _spawn_agent_for_call(call_sid: str, caller: str, called: str) -> None:
    """Background task: create a LiveKit room and start the Viora agent worker."""
    if not settings.livekit_ready:
        logger.warning(
            "LiveKit not configured. Agent would handle: caller=%s called=%s", caller, called
        )
        return

    from livekit import api as lk_api

    room_name = f"viora-call-{call_sid}"
    lk = lk_api.LiveKitAPI(
        url=settings.LIVEKIT_URL,
        api_key=settings.LIVEKIT_API_KEY,
        api_secret=settings.LIVEKIT_API_SECRET,
    )

    try:
        # Create room with call metadata
        await lk.room.create_room(
            lk_api.CreateRoomRequest(
                name=room_name,
                metadata=json.dumps({"caller_phone": caller, "call_sid": call_sid}),
                empty_timeout=300,
            )
        )
        logger.info("LiveKit room created: %s", room_name)
    except Exception as e:
        logger.error("Failed to create LiveKit room: %s", e)


@router.post("/inbound")
@router.post("/inbound-call")
async def inbound_call(
    request: Request,
    background_tasks: BackgroundTasks,
    x_exotel_signature: str | None = Header(default=None),
) -> JSONResponse:
    """
    Called by Exotel when a patient dials the clinic's virtual number.
    Exotel sends a POST with call details; we respond with TwiML-like XML
    to connect the call to our LiveKit agent via WebSocket.
    """
    body = await request.body()

    if not _verify_exotel_signature(body, x_exotel_signature):
        logger.warning("Invalid Exotel signature")
        raise HTTPException(status_code=403, detail="Invalid webhook signature")

    try:
        form = await request.form()
        call_sid = str(form.get("CallSid", f"demo-{uuid.uuid4()}"))
        caller = str(form.get("From", "unknown"))
        called = str(form.get("To", "unknown"))
        str(form.get("CallStatus", "ringing"))

        logger.info("Inbound call | sid=%s | from=%s | to=%s", call_sid, caller, called)

        # Spawn agent in background
        background_tasks.add_task(_spawn_agent_for_call, call_sid, caller, called)

        # Return Exotel connect XML (connect to our LiveKit WebSocket bridge)

        return JSONResponse(
            content={"status": "connected", "room": f"viora-call-{call_sid}"},
            headers={"Content-Type": "application/json"},
        )

    except Exception as e:
        logger.exception("Error processing inbound call: %s", e)
        raise HTTPException(status_code=500, detail="Internal error processing call")


@router.post("/status")
async def call_status_update(request: Request) -> JSONResponse:
    """
    Called by Exotel when call status changes (answered, completed, etc.).
    Used to update call logs.
    """
    form = await request.form()
    call_sid = str(form.get("CallSid", ""))
    status = str(form.get("CallStatus", ""))
    duration = form.get("Duration")

    logger.info("Call status update | sid=%s | status=%s | duration=%s", call_sid, status, duration)
    return JSONResponse({"received": True})
