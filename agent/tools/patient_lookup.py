"""
Viora – Patient Lookup Tool.
Resolves caller phone number to a patient record via HMS.
"""

from __future__ import annotations

import logging

from agent.hms import get_hms_adapter
from agent.hms.base import PatientRecord

logger = logging.getLogger(__name__)


async def lookup_by_phone(phone: str) -> dict:
    """Look up a patient by their calling phone number."""
    hms = get_hms_adapter()
    patient: PatientRecord | None = await hms.get_patient_by_phone(phone)

    if not patient:
        return {"found": False, "is_new_patient": True}

    return {
        "found": True,
        "is_new_patient": False,
        "patient_id": patient.hms_id,
        "name": patient.name,
        "preferred_language": patient.preferred_language,
        "last_visit": patient.last_visit.isoformat() if patient.last_visit else None,
        "known_conditions": patient.known_conditions,
        "current_medications": patient.current_medications,
    }


async def lookup_by_id(hms_id: str) -> dict:
    """Fetch full patient record by HMS ID."""
    hms = get_hms_adapter()
    patient = await hms.get_patient_by_id(hms_id)
    if not patient:
        return {"found": False}
    return {
        "found": True,
        "patient_id": patient.hms_id,
        "name": patient.name,
        "phone": patient.phone,
        "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        "blood_group": patient.blood_group,
        "known_conditions": patient.known_conditions,
        "current_medications": patient.current_medications,
    }
