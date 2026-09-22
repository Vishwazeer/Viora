"""
Viora – Dashboard API.
All routes fall back to structured demo data when the database is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.middleware.auth import require_dashboard_key
from db.models import CallLog, CallOutcome
from db.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_dashboard_key)])

# ─── Demo data (returned when DB is not available) ────────────────────────────

def _demo_calls():
    now = datetime.now(UTC)
    return [
        {
            "id": f"demo-{i}",
            "patient_phone": f"+9198765432{i:02d}",
            "language": ["en-IN", "hi-IN", "mr-IN"][i % 3],
            "primary_intent": ["appointment_book", "lab_report", "opd_timings", "symptom_triage", "faq"][i % 5],
            "outcome": ["resolved", "escalated", "resolved", "abandoned", "resolved"][i % 5],
            "escalation_reason": "patient_requested" if i % 5 == 1 else None,
            "started_at": (now - timedelta(hours=i * 2)).isoformat(),
            "ended_at": (now - timedelta(hours=i * 2 - 0.05)).isoformat(),
            "duration_seconds": 72 + i * 28,
            "turn_count": 3 + i,
            "consent_given": True,
            "sentiment_score": round(0.4 + (i % 5) * 0.12, 2),
            "summary": "Demo call – connect a database to see real data.",
        }
        for i in range(12)
    ]

_DEMO_STATS = {
    "total_calls": 247, "today_calls": 18,
    "resolution_rate": 84.2, "escalation_rate": 8.5,
    "avg_duration_seconds": 142,
    "intents": [
        {"intent": "appointment_book", "count": 89},
        {"intent": "lab_report",       "count": 42},
        {"intent": "opd_timings",      "count": 37},
        {"intent": "prescription_lookup", "count": 31},
        {"intent": "symptom_triage",   "count": 24},
        {"intent": "faq",              "count": 24},
    ],
    "languages": [
        {"language": "en-IN", "count": 138},
        {"language": "hi-IN", "count": 72},
        {"language": "mr-IN", "count": 37},
    ],
    "_demo": True,
}

_DEMO_TRANSCRIPT = [
    {"role": "assistant", "text": "Hello! You've reached the clinic. This call is assisted by Viora. Do you consent to continue?", "language": "en-IN"},
    {"role": "user",      "text": "Yes, please.", "language": "en-IN"},
    {"role": "assistant", "text": "Welcome! How can I help you today?", "language": "en-IN"},
    {"role": "user",      "text": "I need to book an appointment with Dr. Sharma for Friday.", "language": "en-IN"},
    {"role": "assistant", "text": "Dr. Sharma has slots at 10:00 AM and 3:00 PM this Friday. Which works for you?", "language": "en-IN"},
    {"role": "user",      "text": "10 AM please.", "language": "en-IN"},
    {"role": "assistant", "text": "Done! Appointment confirmed with Dr. Sharma on Friday at 10:00 AM. See you then!", "language": "en-IN"},
]

# ─── WebSocket Live Feed ──────────────────────────────────────────────────────

class LiveCallManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event: dict) -> None:
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_live_manager = LiveCallManager()


@router.websocket("/ws/live")
async def live_calls_ws(websocket: WebSocket) -> None:
    await _live_manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        _live_manager.disconnect(websocket)


# ─── Call Logs ────────────────────────────────────────────────────────────────

@router.get("/calls")
async def list_calls(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    language: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        query = select(CallLog).order_by(desc(CallLog.started_at))
        if search:
            query = query.where(CallLog.patient_phone.contains(search))
        if outcome:
            query = query.where(CallLog.outcome == outcome)
        if language:
            query = query.where(CallLog.language == language)
        if date_from:
            query = query.where(CallLog.started_at >= datetime.fromisoformat(date_from))
        if date_to:
            query = query.where(CallLog.started_at <= datetime.fromisoformat(date_to))

        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        offset = (page - 1) * page_size
        calls = (await db.execute(query.offset(offset).limit(page_size))).scalars().all()
        return {
            "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
            "calls": [_serialise_call(c) for c in calls],
        }
    except Exception as e:
        logger.warning("DB unavailable (list_calls): %s", e)
        all_calls = _demo_calls()
        if search:
            all_calls = [c for c in all_calls if search in c["patient_phone"]]
        total = len(all_calls)
        offset = (page - 1) * page_size
        return {
            "total": total, "page": page, "page_size": page_size,
            "pages": max(1, (total + page_size - 1) // page_size),
            "calls": all_calls[offset: offset + page_size],
            "_demo": True,
        }


@router.get("/calls/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        uid = UUID(call_id)
        result = await db.execute(select(CallLog).where(CallLog.id == uid))
        call = result.scalar_one_or_none()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        return _serialise_call(call, include_transcript=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("DB unavailable (get_call): %s", e)
        demo = next((c for c in _demo_calls() if c["id"] == call_id), _demo_calls()[0])
        return {**demo, "transcript": _DEMO_TRANSCRIPT, "_demo": True}


@router.get("/calls/{call_id}/transcript")
async def get_transcript(call_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        uid = UUID(call_id)
        result = await db.execute(select(CallLog).where(CallLog.id == uid))
        call = result.scalar_one_or_none()
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        return {"call_id": call_id, "transcript": call.transcript or []}
    except HTTPException:
        raise
    except Exception:
        return {"call_id": call_id, "transcript": _DEMO_TRANSCRIPT, "_demo": True}


# ─── Escalations ──────────────────────────────────────────────────────────────

@router.get("/escalations")
async def list_escalations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        query = (
            select(CallLog)
            .where(CallLog.outcome == CallOutcome.ESCALATED)
            .order_by(desc(CallLog.started_at))
        )
        total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        calls = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return {"total": total, "calls": [_serialise_call(c) for c in calls]}
    except Exception as e:
        logger.warning("DB unavailable (list_escalations): %s", e)
        now = datetime.now(UTC)
        demo = [
            {"id": "e1", "patient_phone": "+919876543210", "language": "en-IN",
             "escalation_reason": "emergency", "outcome": "escalated",
             "started_at": (now - timedelta(minutes=5)).isoformat(),
             "ended_at": None, "duration_seconds": 38, "turn_count": 2,
             "consent_given": True, "sentiment_score": 0.2, "summary": None,
             "primary_intent": "symptom_triage"},
            {"id": "e2", "patient_phone": "+919988776655", "language": "hi-IN",
             "escalation_reason": "mental_health", "outcome": "escalated",
             "started_at": (now - timedelta(hours=1)).isoformat(),
             "ended_at": None, "duration_seconds": 95, "turn_count": 6,
             "consent_given": True, "sentiment_score": 0.15, "summary": None,
             "primary_intent": "faq"},
            {"id": "e3", "patient_phone": "+919123456789", "language": "mr-IN",
             "escalation_reason": "patient_requested", "outcome": "escalated",
             "started_at": (now - timedelta(hours=3)).isoformat(),
             "ended_at": None, "duration_seconds": 112, "turn_count": 4,
             "consent_given": True, "sentiment_score": 0.35, "summary": None,
             "primary_intent": "appointment_book"},
        ]
        return {"total": len(demo), "calls": demo, "_demo": True}


# ─── Analytics ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    try:
        now = datetime.now(UTC)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        total_calls   = (await db.execute(select(func.count(CallLog.id)))).scalar_one()
        today_calls   = (await db.execute(select(func.count(CallLog.id)).where(CallLog.started_at >= today_start))).scalar_one()
        resolved      = (await db.execute(select(func.count(CallLog.id)).where(CallLog.outcome == CallOutcome.RESOLVED))).scalar_one()
        escalated     = (await db.execute(select(func.count(CallLog.id)).where(CallLog.outcome == CallOutcome.ESCALATED))).scalar_one()
        avg_duration  = (await db.execute(select(func.avg(CallLog.duration_seconds)))).scalar_one()

        resolution_rate  = round((resolved  / total_calls * 100) if total_calls else 0, 1)
        escalation_rate  = round((escalated / total_calls * 100) if total_calls else 0, 1)

        intent_rows = await db.execute(
            select(CallLog.primary_intent, func.count(CallLog.id).label("count"))
            .where(CallLog.started_at >= week_start)
            .group_by(CallLog.primary_intent)
            .order_by(desc("count")).limit(8)
        )
        intents = [{"intent": r[0].value if r[0] else "unknown", "count": r[1]} for r in intent_rows]

        lang_rows = await db.execute(
            select(CallLog.language, func.count(CallLog.id).label("count"))
            .group_by(CallLog.language)
        )
        languages = [{"language": r[0].value if r[0] else "unknown", "count": r[1]} for r in lang_rows]

        return {
            "total_calls": total_calls, "today_calls": today_calls,
            "resolution_rate": resolution_rate, "escalation_rate": escalation_rate,
            "avg_duration_seconds": round(avg_duration or 0),
            "intents": intents, "languages": languages,
        }
    except Exception as e:
        logger.warning("DB unavailable (get_stats): %s", e)
        return _DEMO_STATS


@router.get("/health-status")
async def get_health_status() -> dict:
    from agent.hms import get_hms_adapter
    from config.settings import get_settings
    s = get_settings()
    results = {}
    try:
        hms = get_hms_adapter()
        hms_ok, hms_latency = await hms.health_check()
        results["hms"] = {"ok": hms_ok, "latency_ms": hms_latency, "provider": s.HMS_PROVIDER.value}
    except Exception:
        results["hms"] = {"ok": False, "latency_ms": None, "provider": s.HMS_PROVIDER.value}

    results["sarvam"]  = {"ok": s.sarvam_ready,  "configured": s.sarvam_ready}
    results["gemini"]  = {"ok": s.gemini_ready,   "configured": s.gemini_ready,  "model": s.GEMINI_MODEL}
    results["livekit"] = {"ok": s.livekit_ready,  "configured": s.livekit_ready}
    results["exotel"]  = {"ok": s.exotel_ready,   "configured": s.exotel_ready}

    all_ok  = all(v.get("ok") for v in results.values())
    any_ok  = any(v.get("ok") for v in results.values())
    overall = "healthy" if all_ok else ("degraded" if any_ok else "offline")
    return {"overall": overall, "services": results}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _serialise_call(call: CallLog, include_transcript: bool = False) -> dict:
    d = {
        "id": str(call.id),
        "patient_phone": call.patient_phone,
        "language": call.language.value if call.language else "unknown",
        "primary_intent": call.primary_intent.value if call.primary_intent else "unknown",
        "outcome": call.outcome.value if call.outcome else "unknown",
        "escalation_reason": call.escalation_reason.value if call.escalation_reason else None,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "duration_seconds": call.duration_seconds,
        "turn_count": call.turn_count,
        "consent_given": call.consent_given,
        "sentiment_score": call.sentiment_score,
        "summary": call.summary,
    }
    if include_transcript:
        d["transcript"] = call.transcript or []
    return d
