"""
Viora – Appointment Tool.
Handles booking, cancellation, and rescheduling via the HMS adapter.
All methods return structured dicts that the LLM formats into natural speech.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from agent.hms import get_hms_adapter
from agent.hms.base import TimeSlot

logger = logging.getLogger(__name__)


def _format_slot(slot: TimeSlot) -> str:
    day = slot.start_time.strftime("%A, %d %B")
    time_str = slot.start_time.strftime("%I:%M %p")
    return f"{slot.doctor_name} – {day} at {time_str}"


async def get_available_slots(
    department: str | None = None,
    doctor_name: str | None = None,
    preferred_date_str: str | None = None,
) -> dict:
    """Fetch available appointment slots matching the given preferences."""
    hms = get_hms_adapter()

    preferred_date: date | None = None
    if preferred_date_str:
        try:
            preferred_date = datetime.strptime(preferred_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Resolve doctor name to ID if provided
    doctor_id: str | None = None
    if doctor_name:
        doctors = await hms.list_doctors()
        match = next((d for d in doctors if doctor_name.lower() in d.name.lower()), None)
        if match:
            doctor_id = match.hms_id

    slots = await hms.get_available_slots(
        doctor_id=doctor_id,
        department=department,
        preferred_date=preferred_date,
    )

    if not slots:
        return {
            "found": False,
            "message": "No slots available for the requested time. Try a different date or department.",
        }

    formatted = [
        {
            "slot_id": s.slot_id,
            "display": _format_slot(s),
            "doctor": s.doctor_name,
            "date": s.start_time.strftime("%Y-%m-%d"),
            "time": s.start_time.strftime("%I:%M %p"),
        }
        for s in slots[:4]  # present at most 4 options
    ]

    return {"found": True, "slots": formatted, "count": len(formatted)}


async def book_appointment(
    patient_id: str,
    slot_id: str,
    notes: str | None = None,
) -> dict:
    """Book a specific slot for a patient."""
    hms = get_hms_adapter()
    try:
        appt = await hms.book_appointment(patient_id, slot_id, notes)
        return {
            "success": True,
            "appointment_id": appt.appointment_id,
            "doctor": appt.doctor_name,
            "department": appt.department,
            "date_time": appt.appointment_time.strftime("%A, %d %B at %I:%M %p"),
            "status": appt.status,
        }
    except ValueError as e:
        logger.warning("Slot booking failed: %s", e)
        return {"success": False, "message": str(e)}


async def cancel_appointment(appointment_id: str, reason: str | None = None) -> dict:
    """Cancel an existing appointment."""
    hms = get_hms_adapter()
    success = await hms.cancel_appointment(appointment_id, reason)
    return {
        "success": success,
        "message": "Appointment cancelled successfully." if success
                   else "Could not find that appointment. Please check the details.",
    }


async def reschedule_appointment(appointment_id: str, new_slot_id: str) -> dict:
    """Move an appointment to a new slot."""
    hms = get_hms_adapter()
    try:
        appt = await hms.reschedule_appointment(appointment_id, new_slot_id)
        return {
            "success": True,
            "appointment_id": appt.appointment_id,
            "new_date_time": appt.appointment_time.strftime("%A, %d %B at %I:%M %p"),
            "doctor": appt.doctor_name,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


async def get_patient_appointments(patient_id: str) -> dict:
    """Retrieve upcoming appointments for a patient."""
    hms = get_hms_adapter()
    appts = await hms.get_patient_appointments(patient_id, upcoming_only=True)
    if not appts:
        return {"found": False, "message": "No upcoming appointments found."}
    return {
        "found": True,
        "appointments": [
            {
                "appointment_id": a.appointment_id,
                "doctor": a.doctor_name,
                "department": a.department,
                "date_time": a.appointment_time.strftime("%A, %d %B at %I:%M %p"),
                "status": a.status,
            }
            for a in appts
        ],
    }


async def list_doctors(department: str | None = None) -> dict:
    """List available doctors, optionally filtered by department."""
    hms = get_hms_adapter()
    doctors = await hms.list_doctors(department)
    return {
        "doctors": [
            {
                "name": d.name,
                "specialisation": d.specialisation,
                "department": d.department,
                "available_days": ", ".join(d.available_days),
                "fee": f"₹{d.consultation_fee:.0f}" if d.consultation_fee else "N/A",
            }
            for d in doctors
        ]
    }
