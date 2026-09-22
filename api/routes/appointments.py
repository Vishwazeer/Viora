"""
Viora – Appointments & SMS Demo API routes.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.middleware.auth import require_dashboard_key

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Response Models ──────────────────────────────────────────────────────────

class AppointmentOut(BaseModel):
    id: str
    patient_name: str
    patient_phone: str
    doctor_name: str
    department: str | None
    appointment_date: str
    appointment_time: str
    reason: str | None
    status: str
    booked_via: str
    created_at: str

    class Config:
        from_attributes = True


class SMSOut(BaseModel):
    id: str
    recipient_name: str | None
    recipient_phone: str
    message_body: str
    message_type: str
    status: str
    sent_at: str
    appointment_id: str | None

    class Config:
        from_attributes = True


# ─── Appointments ─────────────────────────────────────────────────────────────

@router.get("/", dependencies=[Depends(require_dashboard_key)])
async def list_appointments(
    status: str | None = Query(None),
    doctor: str | None = Query(None),
    limit: int = Query(50, le=200),
) -> JSONResponse:
    """List all appointments, optionally filtered by status or doctor name."""
    try:
        from sqlalchemy import desc, select

        from db.models import Appointment
        from db.session import get_db_context

        async with get_db_context() as db:
            q = select(Appointment).order_by(desc(Appointment.created_at)).limit(limit)
            if status:
                q = q.where(Appointment.status == status)
            if doctor:
                q = q.where(Appointment.doctor_name.ilike(f"%{doctor}%"))

            result = await db.execute(q)
            appts = result.scalars().all()

        return JSONResponse([
            {
                "id": str(a.id),
                "patient_name": a.patient_name,
                "patient_phone": a.patient_phone,
                "doctor_name": a.doctor_name,
                "department": a.department,
                "appointment_date": a.appointment_date,
                "appointment_time": a.appointment_time,
                "reason": a.reason,
                "status": a.status,
                "booked_via": a.booked_via,
                "created_at": a.created_at.isoformat(),
            }
            for a in appts
        ])
    except Exception as e:
        logger.error("Failed to list appointments: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", dependencies=[Depends(require_dashboard_key)])
async def appointment_stats() -> JSONResponse:
    """Quick stats for the appointments dashboard card."""
    try:
        from sqlalchemy import func, select

        from db.models import Appointment
        from db.session import get_db_context

        async with get_db_context() as db:
            total = await db.scalar(select(func.count(Appointment.id)))
            confirmed = await db.scalar(
                select(func.count(Appointment.id)).where(Appointment.status == "confirmed")
            )

        return JSONResponse({"total": total or 0, "confirmed": confirmed or 0})
    except Exception as e:
        logger.warning("Appointment stats unavailable: %s", e)
        return JSONResponse({"total": 0, "confirmed": 0})


@router.delete("/{appointment_id}", dependencies=[Depends(require_dashboard_key)])
async def cancel_appointment_admin(appointment_id: UUID) -> JSONResponse:
    """Cancel an appointment from the admin dashboard."""
    try:
        from sqlalchemy import select

        from db.models import Appointment, AppointmentStatus
        from db.session import get_db_context

        async with get_db_context() as db:
            result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
            appt = result.scalar_one_or_none()
            if not appt:
                raise HTTPException(status_code=404, detail="Appointment not found")
            appt.status = AppointmentStatus.CANCELLED

        return JSONResponse({"cancelled": True, "id": str(appointment_id)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── SMS Demo Log ─────────────────────────────────────────────────────────────

@router.get("/sms-log", dependencies=[Depends(require_dashboard_key)])
async def list_sms_log(limit: int = Query(50, le=200)) -> JSONResponse:
    """Return all demo SMS notifications — shows what would be sent to patients."""
    try:
        from sqlalchemy import desc, select

        from db.models import SMSLog
        from db.session import get_db_context

        async with get_db_context() as db:
            q = select(SMSLog).order_by(desc(SMSLog.sent_at)).limit(limit)
            result = await db.execute(q)
            logs = result.scalars().all()

        return JSONResponse([
            {
                "id": str(s.id),
                "recipient_name": s.recipient_name,
                "recipient_phone": s.recipient_phone,
                "message_body": s.message_body,
                "message_type": s.message_type,
                "status": s.status,
                "sent_at": s.sent_at.isoformat(),
                "appointment_id": str(s.appointment_id) if s.appointment_id else None,
            }
            for s in logs
        ])
    except Exception as e:
        logger.error("Failed to fetch SMS log: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
