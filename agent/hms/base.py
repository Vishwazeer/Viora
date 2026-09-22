"""
Viora – HMS Adapter Abstract Base Class.
Every Hospital Management System integration must implement this interface.
Swap the concrete implementation via the HMS_PROVIDER env var.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime

# ─── Domain DTOs ─────────────────────────────────────────────────────────────

@dataclass
class PatientRecord:
    hms_id: str
    name: str
    phone: str
    date_of_birth: date | None = None
    gender: str | None = None
    blood_group: str | None = None
    email: str | None = None
    address: str | None = None
    known_conditions: list[str] = field(default_factory=list)
    current_medications: list[str] = field(default_factory=list)
    last_visit: date | None = None
    preferred_language: str = "en-IN"


@dataclass
class Doctor:
    hms_id: str
    name: str
    specialisation: str
    department: str
    available_days: list[str] = field(default_factory=list)
    consultation_fee: float | None = None


@dataclass
class TimeSlot:
    slot_id: str
    doctor_id: str
    doctor_name: str
    start_time: datetime
    end_time: datetime
    is_available: bool = True


@dataclass
class Appointment:
    appointment_id: str
    patient_id: str
    doctor_id: str
    doctor_name: str
    department: str
    appointment_time: datetime
    status: str  # "scheduled" | "cancelled" | "completed" | "no_show"
    notes: str | None = None


@dataclass
class LabReport:
    report_id: str
    patient_id: str
    test_name: str
    ordered_date: date
    status: str         # "pending" | "ready" | "dispatched"
    result_summary: str | None = None
    ready_date: date | None = None


@dataclass
class Prescription:
    prescription_id: str
    patient_id: str
    doctor_name: str
    issued_date: date
    medications: list[dict]   # [{name, dosage, frequency, duration}]
    notes: str | None = None
    refill_allowed: bool = False


@dataclass
class BillSummary:
    bill_id: str
    patient_id: str
    total_amount: float
    paid_amount: float
    outstanding: float
    currency: str = "INR"
    last_updated: date | None = None


# ─── Abstract Adapter ─────────────────────────────────────────────────────────

class HMSAdapter(ABC):
    """
    Abstract interface for Hospital Management System integrations.
    All methods are async to support both REST APIs and local DB queries.
    """

    # ── Patient ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def get_patient_by_phone(self, phone: str) -> PatientRecord | None:
        """Look up a patient by their registered phone number."""
        ...

    @abstractmethod
    async def get_patient_by_id(self, hms_id: str) -> PatientRecord | None:
        """Fetch a full patient record by HMS ID."""
        ...

    @abstractmethod
    async def register_new_patient_draft(
        self,
        name: str,
        phone: str,
        chief_complaint: str,
        preferred_language: str = "en-IN",
    ) -> str:
        """
        Create a draft new-patient record and return the new HMS patient ID.
        The record is flagged for staff completion.
        """
        ...

    # ── Appointments ──────────────────────────────────────────────────────────

    @abstractmethod
    async def get_available_slots(
        self,
        doctor_id: str | None = None,
        department: str | None = None,
        preferred_date: date | None = None,
    ) -> list[TimeSlot]:
        """Return available appointment slots matching the given filters."""
        ...

    @abstractmethod
    async def book_appointment(
        self,
        patient_id: str,
        slot_id: str,
        notes: str | None = None,
    ) -> Appointment:
        """Book the given slot for the patient and return the confirmed appointment."""
        ...

    @abstractmethod
    async def cancel_appointment(self, appointment_id: str, reason: str | None = None) -> bool:
        """Cancel an appointment. Returns True on success."""
        ...

    @abstractmethod
    async def reschedule_appointment(
        self, appointment_id: str, new_slot_id: str
    ) -> Appointment:
        """Move an existing appointment to a new slot."""
        ...

    @abstractmethod
    async def get_patient_appointments(
        self, patient_id: str, upcoming_only: bool = True
    ) -> list[Appointment]:
        """Return a patient's appointment history or upcoming appointments."""
        ...

    # ── Doctors ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def list_doctors(self, department: str | None = None) -> list[Doctor]:
        """Return all doctors, optionally filtered by department."""
        ...

    # ── Lab Reports ───────────────────────────────────────────────────────────

    @abstractmethod
    async def get_lab_reports(self, patient_id: str) -> list[LabReport]:
        """Return all lab reports for a patient, most recent first."""
        ...

    # ── Prescriptions ─────────────────────────────────────────────────────────

    @abstractmethod
    async def get_prescriptions(self, patient_id: str) -> list[Prescription]:
        """Return active prescriptions for a patient."""
        ...

    # ── Billing ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def get_bill_summary(self, patient_id: str) -> BillSummary | None:
        """Return the outstanding bill summary for a patient."""
        ...

    # ── Health Check ──────────────────────────────────────────────────────────

    @abstractmethod
    async def health_check(self) -> tuple[bool, int]:
        """
        Ping the HMS backend.
        Returns (is_healthy: bool, latency_ms: int).
        """
        ...
