"""
Viora – Agent Tools for Viora Health.
These functions are exposed to the LLM via function calling.
Each tool either writes to the DB or simulates an external action (SMS demo).
"""
from __future__ import annotations

import logging
import uuid

from livekit.agents.llm import function_tool

logger = logging.getLogger(__name__)

# ─── Viora Health Knowledge Base ─────────────────────────────────────

CLINIC_INFO = {
    "name": "Viora Health",
    "address": "42, MG Road, Koramangala, Bangalore - 560095",
    "phone": "+91-80-4567-8900",
    "email": "care@healinghandsclinic.in",
    "opd_hours": "Monday to Saturday: 9:00 AM to 7:00 PM | Sunday: 10:00 AM to 2:00 PM",
    "emergency": "24x7 Emergency: +91-80-4567-8999",
}

DOCTORS = {
    "dr_priya_sharma": {
        "name": "Dr. Priya Sharma",
        "department": "General Medicine",
        "available_days": ["Monday", "Wednesday", "Friday"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM", "4:00 PM"],
        "fee": 600,
    },
    "dr_rajan_mehta": {
        "name": "Dr. Rajan Mehta",
        "department": "Orthopedics",
        "available_days": ["Tuesday", "Thursday", "Saturday"],
        "slots": ["10:00 AM", "11:00 AM", "12:00 PM", "3:00 PM", "4:00 PM"],
        "fee": 800,
    },
    "dr_ananya_iyer": {
        "name": "Dr. Ananya Iyer",
        "department": "Pediatrics",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "2:00 PM", "3:00 PM"],
        "fee": 650,
    },
    "dr_suresh_nair": {
        "name": "Dr. Suresh Nair",
        "department": "Cardiology",
        "available_days": ["Monday", "Wednesday", "Friday"],
        "slots": ["11:00 AM", "12:00 PM", "2:00 PM", "5:00 PM"],
        "fee": 1200,
    },
    "dr_kavya_reddy": {
        "name": "Dr. Kavya Reddy",
        "department": "Dermatology",
        "available_days": ["Tuesday", "Thursday", "Saturday"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM", "3:00 PM", "4:00 PM"],
        "fee": 700,
    },
}

SERVICES = [
    "Blood Tests (CBC, LFT, KFT, HbA1c, Thyroid)",
    "ECG and 2D Echo",
    "X-Ray and Ultrasound",
    "Physiotherapy",
    "Vaccination (Adult and Paediatric)",
    "Minor Surgery and Wound Dressing",
    "Diabetes Management Clinic",
    "Hypertension Clinic",
]


# ─── SMS Helper ───────────────────────────────────────────────────────────────

async def _log_sms(
    *,
    phone: str,
    name: str,
    message: str,
    message_type: str,
    appointment_id: uuid.UUID | None = None,
) -> None:
    """Store an SMS in the demo log. In production this calls Exotel."""
    try:
        from db.models import SMSLog, SMSStatus
        from db.session import get_db_context

        async with get_db_context() as db:
            sms = SMSLog(
                appointment_id=appointment_id,
                recipient_phone=phone,
                recipient_name=name,
                message_body=message,
                message_type=message_type,
                status=SMSStatus.DEMO,
            )
            db.add(sms)
        logger.info("SMS demo logged | to=%s | type=%s", phone, message_type)
    except Exception as e:
        logger.warning("Could not log SMS (non-fatal): %s", e)


# ─── Agent Tools ─────────────────────────────────────────────────────────────

@function_tool
async def get_clinic_info() -> str:
    """
    Returns general information about Viora Health including address,
    timings, emergency contact, and available services.
    """
    services_list = ", ".join(SERVICES[:5])
    return (
        f"Viora Health is located at {CLINIC_INFO['address']}. "
        f"OPD Hours: {CLINIC_INFO['opd_hours']}. "
        f"Phone: {CLINIC_INFO['phone']}. "
        f"Emergency (24x7): {CLINIC_INFO['emergency']}. "
        f"Key services include: {services_list}, and more."
    )


@function_tool
async def list_doctors(department: str = "") -> str:
    """
    Lists available doctors at Viora Health.
    Optionally filter by department name such as General Medicine, Orthopedics, Pediatrics, Cardiology, or Dermatology.
    department: Optional department filter string.
    """
    docs = list(DOCTORS.values())
    if department:
        docs = [d for d in docs if department.lower() in d["department"].lower()]

    if not docs:
        return (
            f"No doctors found for department '{department}'. "
            "Available departments: General Medicine, Orthopedics, Pediatrics, Cardiology, Dermatology."
        )

    result = "Available doctors at Viora Health: "
    parts = []
    for doc in docs:
        days = ", ".join(doc["available_days"])
        parts.append(f"{doc['name']} in {doc['department']}, available {days}, fee Rs.{doc['fee']}")
    return result + "; ".join(parts) + "."


@function_tool
async def check_doctor_availability(doctor_name: str, day: str) -> str:
    """
    Checks a specific doctor's availability on a given day.
    doctor_name: Doctor's name, e.g. Dr. Priya Sharma.
    day: Day of the week, e.g. Monday, Tuesday.
    """
    for doc in DOCTORS.values():
        if doctor_name.lower() in doc["name"].lower():
            if day.capitalize() in doc["available_days"]:
                slots = ", ".join(doc["slots"])
                return (
                    f"{doc['name']} is available on {day.capitalize()}. "
                    f"Available slots: {slots}. Consultation fee: Rs.{doc['fee']}."
                )
            else:
                available = ", ".join(doc["available_days"])
                return (
                    f"{doc['name']} is not available on {day.capitalize()}. "
                    f"They are available on: {available}."
                )

    return f"I could not find a doctor named '{doctor_name}'. Shall I list all our doctors?"


@function_tool
async def book_appointment(
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    appointment_date: str,
    appointment_time: str,
    reason: str = "",
) -> str:
    """
    Books an appointment at Viora Health and sends an SMS confirmation.
    patient_name: Full name of the patient.
    patient_phone: Patient's 10-digit phone number.
    doctor_name: Name of the doctor, e.g. Dr. Priya Sharma.
    appointment_date: Date such as Monday 19th May or next Tuesday.
    appointment_time: Time such as 10:00 AM.
    reason: Reason for the visit, optional.
    """
    # Find the doctor for department and fee info
    department = "General"
    fee = 0
    for doc in DOCTORS.values():
        if doctor_name.lower() in doc["name"].lower():
            department = doc["department"]
            fee = doc["fee"]
            break

    appointment_id = uuid.uuid4()
    confirmation_ref = str(appointment_id)[:8].upper()

    sms_message = (
        f"Dear {patient_name},\n"
        f"Your appointment at Viora Health is CONFIRMED.\n"
        f"Doctor: {doctor_name} ({department})\n"
        f"Date & Time: {appointment_date} at {appointment_time}\n"
        f"Address: 42, MG Road, Koramangala, Bangalore\n"
        f"Ref No: HHC-{confirmation_ref}\n"
        f"Please arrive 15 mins early. Fee: Rs.{fee}.\n"
        f"To cancel or reschedule, call: +91-80-4567-8900\n"
        f"[Demo Mode: SMS via Exotel in production]"
    )

    # Persist appointment to DB (best-effort)
    try:
        from db.models import Appointment, AppointmentStatus
        from db.session import get_db_context

        async with get_db_context() as db:
            appt = Appointment(
                id=appointment_id,
                patient_name=patient_name,
                patient_phone=patient_phone,
                doctor_name=doctor_name,
                department=department,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                reason=reason or None,
                status=AppointmentStatus.CONFIRMED,
                booked_via="voice_agent",
            )
            db.add(appt)
        logger.info(
            "Appointment booked | ref=HHC-%s | patient=%s | doctor=%s",
            confirmation_ref, patient_name, doctor_name,
        )
    except Exception as e:
        logger.warning("Could not persist appointment (continuing): %s", e)

    # Log demo SMS
    await _log_sms(
        phone=patient_phone,
        name=patient_name,
        message=sms_message,
        message_type="appointment_confirmation",
        appointment_id=appointment_id,
    )

    return (
        f"Done! Your appointment is confirmed. Reference number HHC-{confirmation_ref}. "
        f"{patient_name} is booked with {doctor_name} on {appointment_date} at {appointment_time}. "
        f"An SMS confirmation has been sent to {patient_phone}."
    )


@function_tool
async def cancel_appointment(confirmation_ref: str, patient_phone: str) -> str:
    """
    Cancels an existing appointment using the booking reference number.
    confirmation_ref: The HHC reference number from the confirmation SMS.
    patient_phone: Patient's phone number for verification.
    """
    return (
        f"I have submitted a cancellation request for reference {confirmation_ref}. "
        f"Our team will confirm via SMS to {patient_phone} within 30 minutes. "
        f"You can also call us at +91-80-4567-8900."
    )
