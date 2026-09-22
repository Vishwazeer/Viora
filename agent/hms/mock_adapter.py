"""
Viora – Mock HMS Adapter.
Realistic deterministic fake hospital data for dev/testing/demos.
No external API credentials required.
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import date, datetime, timedelta

from agent.hms.base import (
    Appointment,
    BillSummary,
    Doctor,
    HMSAdapter,
    LabReport,
    PatientRecord,
    Prescription,
    TimeSlot,
)

# ─── Seed Data ────────────────────────────────────────────────────────────────

_DOCTORS: list[Doctor] = [
    Doctor("DR001", "Dr. Arjun Sharma", "Gastroenterology & Proctology", "Gastroenterology",
           ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], 800.0),
    Doctor("DR002", "Dr. Priya Mehta", "General Surgery", "Surgery",
           ["Monday","Tuesday","Wednesday","Thursday","Friday"], 700.0),
    Doctor("DR003", "Dr. Rajesh Nair", "Internal Medicine", "Internal Medicine",
           ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"], 600.0),
    Doctor("DR004", "Dr. Sunita Kulkarni", "Dietetics & Nutrition", "Nutrition",
           ["Tuesday","Thursday","Saturday"], 500.0),
    Doctor("DR005", "Dr. Vikram Desai", "Laparoscopic Surgery", "Surgery",
           ["Monday","Wednesday","Friday"], 900.0),
]

_PATIENTS: list[PatientRecord] = [
    PatientRecord("PT001","Ramesh Joshi","+919876543210",date(1975,3,14),"Male","B+",
                  known_conditions=["Type 2 Diabetes","Hypertension"],
                  current_medications=["Metformin 500mg","Amlodipine 5mg"],
                  last_visit=date.today()-timedelta(days=30), preferred_language="hi-IN"),
    PatientRecord("PT002","Priya Patil","+919988776655",date(1990,7,22),"Female","O+",
                  known_conditions=["Irritable Bowel Syndrome"],
                  current_medications=["Mebeverine 135mg"],
                  last_visit=date.today()-timedelta(days=14), preferred_language="mr-IN"),
    PatientRecord("PT003","Suresh Kumar","+919123456789",date(1965,11,5),"Male","A+",
                  known_conditions=["Piles Grade II","Constipation"],
                  current_medications=["Duphalac Syrup"],
                  last_visit=date.today()-timedelta(days=7), preferred_language="hi-IN"),
    PatientRecord("PT004","Anita Fernandes","+919812345678",date(1988,4,16),"Female","AB+",
                  last_visit=date.today()-timedelta(days=60), preferred_language="en-IN"),
    PatientRecord("PT005","Mohan Reddy","+919700000001",date(1958,9,30),"Male","B-",
                  known_conditions=["Fistula-in-ano","Anaemia"],
                  current_medications=["Iron supplements","Folic acid"],
                  last_visit=date.today()-timedelta(days=3), preferred_language="en-IN"),
]

_PATIENT_PHONE_INDEX: dict[str, PatientRecord] = {}
for _p in _PATIENTS:
    _PATIENT_PHONE_INDEX[_p.phone] = _p
    _PATIENT_PHONE_INDEX[_p.phone.lstrip("+")] = _p

_APPOINTMENTS: dict[str, Appointment] = {}


def _generate_slots(days_ahead: int = 7) -> list[TimeSlot]:
    slots: list[TimeSlot] = []
    slot_hours = [9, 10, 11, 15, 16, 17]
    for offset in range(1, days_ahead + 1):
        slot_date = date.today() + timedelta(days=offset)
        weekday = slot_date.strftime("%A")
        for doctor in _DOCTORS:
            if weekday not in doctor.available_days:
                continue
            for hour in slot_hours:
                start = datetime(slot_date.year, slot_date.month, slot_date.day, hour)
                slots.append(TimeSlot(
                    slot_id=f"{doctor.hms_id}-{slot_date.isoformat()}-{hour:02d}00",
                    doctor_id=doctor.hms_id,
                    doctor_name=doctor.name,
                    start_time=start,
                    end_time=start + timedelta(minutes=30),
                    is_available=random.random() > 0.3,  # noqa: S311
                ))
    return slots


class MockHMSAdapter(HMSAdapter):
    """Self-contained mock HMS. No credentials required."""

    def __init__(self) -> None:
        self._slots = _generate_slots()

    async def get_patient_by_phone(self, phone: str) -> PatientRecord | None:
        norm = phone.strip().replace(" ", "")
        for key, patient in _PATIENT_PHONE_INDEX.items():
            if key.endswith(norm[-10:]):
                return patient
        return None

    async def get_patient_by_id(self, hms_id: str) -> PatientRecord | None:
        return next((p for p in _PATIENTS if p.hms_id == hms_id), None)

    async def register_new_patient_draft(self, name: str, phone: str,
                                          chief_complaint: str, preferred_language: str = "en-IN") -> str:
        new_id = f"PT{str(uuid.uuid4())[:6].upper()}"
        p = PatientRecord(hms_id=new_id, name=name, phone=phone, preferred_language=preferred_language)
        _PATIENTS.append(p)
        _PATIENT_PHONE_INDEX[phone] = p
        return new_id

    async def get_available_slots(self, doctor_id: str | None = None,
                                   department: str | None = None,
                                   preferred_date: date | None = None) -> list[TimeSlot]:
        slots = [s for s in self._slots if s.is_available]
        if doctor_id:
            slots = [s for s in slots if s.doctor_id == doctor_id]
        if department:
            ids = {d.hms_id for d in _DOCTORS if department.lower() in d.department.lower()}
            slots = [s for s in slots if s.doctor_id in ids]
        if preferred_date:
            slots = [s for s in slots if s.start_time.date() == preferred_date]
        return slots[:8]

    async def book_appointment(self, patient_id: str, slot_id: str,
                                notes: str | None = None) -> Appointment:
        slot = next((s for s in self._slots if s.slot_id == slot_id), None)
        if not slot or not slot.is_available:
            raise ValueError(f"Slot {slot_id} unavailable.")
        slot.is_available = False
        doctor = next(d for d in _DOCTORS if d.hms_id == slot.doctor_id)
        appt = Appointment(
            appointment_id=f"APT{str(uuid.uuid4())[:8].upper()}",
            patient_id=patient_id, doctor_id=slot.doctor_id,
            doctor_name=slot.doctor_name, department=doctor.department,
            appointment_time=slot.start_time, status="scheduled", notes=notes,
        )
        _APPOINTMENTS[appt.appointment_id] = appt
        return appt

    async def cancel_appointment(self, appointment_id: str, reason: str | None = None) -> bool:
        appt = _APPOINTMENTS.get(appointment_id)
        if not appt:
            return False
        appt.status = "cancelled"
        for s in self._slots:
            if s.doctor_id == appt.doctor_id and s.start_time == appt.appointment_time:
                s.is_available = True
                break
        return True

    async def reschedule_appointment(self, appointment_id: str, new_slot_id: str) -> Appointment:
        appt = _APPOINTMENTS.get(appointment_id)
        if not appt:
            raise ValueError(f"Appointment {appointment_id} not found.")
        await self.cancel_appointment(appointment_id)
        return await self.book_appointment(appt.patient_id, new_slot_id)

    async def get_patient_appointments(self, patient_id: str, upcoming_only: bool = True) -> list[Appointment]:
        appts = [a for a in _APPOINTMENTS.values() if a.patient_id == patient_id]
        if upcoming_only:
            now = datetime.now()
            appts = [a for a in appts if a.appointment_time > now and a.status == "scheduled"]
        return sorted(appts, key=lambda a: a.appointment_time)

    async def list_doctors(self, department: str | None = None) -> list[Doctor]:
        if department:
            return [d for d in _DOCTORS if department.lower() in d.department.lower()]
        return list(_DOCTORS)

    async def get_lab_reports(self, patient_id: str) -> list[LabReport]:
        data: dict[str, list[LabReport]] = {
            "PT001": [
                LabReport("LR001","PT001","HbA1c",date.today()-timedelta(days=5),"ready",
                          "7.2% – Moderate control.",date.today()-timedelta(days=2)),
                LabReport("LR002","PT001","Lipid Profile",date.today()-timedelta(days=1),"pending"),
            ],
            "PT003": [
                LabReport("LR003","PT003","Colonoscopy Biopsy",date.today()-timedelta(days=10),"ready",
                          "No malignancy detected.",date.today()-timedelta(days=3)),
            ],
            "PT005": [
                LabReport("LR004","PT005","Complete Blood Count",date.today()-timedelta(days=2),"pending"),
            ],
        }
        return data.get(patient_id, [])

    async def get_prescriptions(self, patient_id: str) -> list[Prescription]:
        data: dict[str, list[Prescription]] = {
            "PT001": [Prescription("RX001","PT001","Dr. Rajesh Nair",date.today()-timedelta(days=30),
                [{"name":"Metformin","dosage":"500mg","frequency":"Twice daily","duration":"3 months"},
                 {"name":"Amlodipine","dosage":"5mg","frequency":"Once daily","duration":"Ongoing"}],
                refill_allowed=True)],
            "PT002": [Prescription("RX002","PT002","Dr. Arjun Sharma",date.today()-timedelta(days=14),
                [{"name":"Mebeverine","dosage":"135mg","frequency":"Three times daily","duration":"1 month"}],
                refill_allowed=True)],
        }
        return data.get(patient_id, [])

    async def get_bill_summary(self, patient_id: str) -> BillSummary | None:
        data: dict[str, BillSummary] = {
            "PT001": BillSummary("BILL001","PT001",2400.0,1600.0,800.0,last_updated=date.today()-timedelta(days=5)),
            "PT003": BillSummary("BILL003","PT003",5000.0,5000.0,0.0,last_updated=date.today()-timedelta(days=7)),
        }
        return data.get(patient_id)

    async def health_check(self) -> tuple[bool, int]:
        t = time.monotonic()
        _ = len(_PATIENTS)
        return True, max(1, int((time.monotonic() - t) * 1000))
