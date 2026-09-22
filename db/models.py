"""
Viora – SQLAlchemy async database models.
All models include DPDP Act compliance fields (consent, audit, retention).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all Viora models."""
    pass


# ─── Enumerations ────────────────────────────────────────────────────────────

class Language(StrEnum):
    ENGLISH = "en-IN"
    HINDI = "hi-IN"
    MARATHI = "mr-IN"
    UNKNOWN = "unknown"


class CallOutcome(StrEnum):
    RESOLVED = "resolved"           # AI handled fully
    ESCALATED = "escalated"         # Transferred to human
    ABANDONED = "abandoned"         # Patient hung up
    FAILED = "failed"               # Technical failure


class AppointmentStatus(StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class SMSStatus(StrEnum):
    SENT = "sent"           # Would be sent via Exotel in production
    DEMO = "demo"           # Logged for visual demo only


class CallIntent(StrEnum):
    APPOINTMENT_BOOK = "appointment_book"
    APPOINTMENT_CANCEL = "appointment_cancel"
    APPOINTMENT_RESCHEDULE = "appointment_reschedule"
    DOCTOR_AVAILABILITY = "doctor_availability"
    OPD_TIMINGS = "opd_timings"
    LAB_REPORT = "lab_report"
    PRESCRIPTION = "prescription"
    SYMPTOM_TRIAGE = "symptom_triage"
    REGISTRATION = "registration"
    BILLING = "billing"
    INSURANCE = "insurance"
    FAQ = "faq"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class EscalationReason(StrEnum):
    EMERGENCY = "emergency"
    PATIENT_REQUESTED = "patient_requested"
    MAX_CLARIFICATIONS = "max_clarifications"
    TECHNICAL_FAILURE = "technical_failure"
    SENSITIVE_COMPLAINT = "sensitive_complaint"
    MENTAL_HEALTH = "mental_health"


class TriageRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EMERGENCY = "emergency"


class AuditEventType(StrEnum):
    CALL_START = "call_start"
    CALL_END = "call_end"
    CONSENT_GIVEN = "consent_given"
    CONSENT_REFUSED = "consent_refused"
    ESCALATION = "escalation"
    TOOL_CALLED = "tool_called"
    DATA_ACCESS = "data_access"
    DATA_DELETE = "data_delete"
    LANGUAGE_SWITCH = "language_switch"
    EMERGENCY_DETECTED = "emergency_detected"


# ─── Models ──────────────────────────────────────────────────────────────────

class Patient(Base):
    """
    Cached patient reference from HMS.
    We store minimal PII — only what's needed for call personalisation.
    """
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    hms_patient_id: Mapped[str | None] = mapped_column(String(128), index=True, unique=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str | None] = mapped_column(String(256))
    preferred_language: Mapped[Language] = mapped_column(
        Enum(Language), default=Language.ENGLISH
    )
    is_known_patient: Mapped[bool] = mapped_column(Boolean, default=False)
    # DPDP: allow patient to request full data erasure
    data_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    call_logs: Mapped[list[CallLog]] = relationship(back_populates="patient", lazy="selectin")


class CallLog(Base):
    """
    Full record of every inbound call. Source of truth for the dashboard.
    """
    __tablename__ = "call_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    exotel_call_sid: Mapped[str | None] = mapped_column(String(128), index=True, unique=True)
    livekit_room_name: Mapped[str | None] = mapped_column(String(256))

    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True
    )
    patient_phone: Mapped[str] = mapped_column(String(20))  # retained for audit even if patient deleted

    language: Mapped[Language] = mapped_column(Enum(Language), default=Language.ENGLISH)
    primary_intent: Mapped[CallIntent] = mapped_column(Enum(CallIntent), default=CallIntent.UNKNOWN)
    outcome: Mapped[CallOutcome] = mapped_column(Enum(CallOutcome), default=CallOutcome.ABANDONED)
    escalation_reason: Mapped[EscalationReason | None] = mapped_column(
        Enum(EscalationReason), nullable=True
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Conversation
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    transcript: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{role, text, ts, lang}]
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)      # post-call AI summary

    # Quality
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)   # -1.0 to 1.0
    resolution_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0.0 to 1.0

    # DPDP
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_delete_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    patient: Mapped[Patient | None] = relationship(back_populates="call_logs")
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="call_log", lazy="selectin")
    triage_records: Mapped[list[TriageRecord]] = relationship(back_populates="call_log")


class AuditEvent(Base):
    """
    Immutable append-only audit log. Required by DPDP Act.
    Never update or delete rows from this table.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("call_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[AuditEventType] = mapped_column(Enum(AuditEventType), index=True)
    actor: Mapped[str] = mapped_column(String(64), default="viora_agent")  # who triggered it
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # event-specific payload
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    call_log: Mapped[CallLog | None] = relationship(back_populates="audit_events")


class TriageRecord(Base):
    """
    Structured symptom intake output. Retained for clinical review.
    """
    __tablename__ = "triage_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_logs.id", ondelete="CASCADE"), index=True
    )
    patient_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    patient_gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    chief_complaint: Mapped[str] = mapped_column(Text)
    symptoms: Mapped[list] = mapped_column(JSON, default=list)           # [str]
    duration_of_symptoms: Mapped[str | None] = mapped_column(String(128), nullable=True)
    risk_level: Mapped[TriageRisk] = mapped_column(Enum(TriageRisk))
    risk_score: Mapped[int] = mapped_column(Integer)                     # 0–100
    recommended_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call_log: Mapped[CallLog] = relationship(back_populates="triage_records")


class ConsentRecord(Base):
    """
    Explicit consent log (DPDP Act Article 6).
    Separate table for quick compliance queries.
    """
    __tablename__ = "consent_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("call_logs.id", ondelete="CASCADE"), index=True
    )
    phone_number: Mapped[str] = mapped_column(String(20))
    consent_given: Mapped[bool] = mapped_column(Boolean)
    consent_method: Mapped[str] = mapped_column(String(32))   # "voice" | "dtmf"
    language: Mapped[Language] = mapped_column(Enum(Language))
    purpose: Mapped[str] = mapped_column(Text)                # exact purpose stated to patient
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SystemHealthSnapshot(Base):
    """
    Periodic health snapshots written by the monitoring task.
    Powers the SystemHealth dashboard page.
    """
    __tablename__ = "system_health_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sarvam_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gemini_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hms_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_calls: Mapped[int] = mapped_column(Integer, default=0)
    sarvam_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    gemini_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    hms_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    livekit_ok: Mapped[bool] = mapped_column(Boolean, default=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Appointment(Base):
    """
    Stores appointments booked by the AI agent during calls.
    """
    __tablename__ = "appointments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    call_log_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("call_logs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    patient_name: Mapped[str] = mapped_column(String(256))
    patient_phone: Mapped[str] = mapped_column(String(20), index=True)
    doctor_name: Mapped[str] = mapped_column(String(256))
    department: Mapped[str | None] = mapped_column(String(128), nullable=True)
    appointment_date: Mapped[str] = mapped_column(String(64))   # "Monday 3rd June" etc.
    appointment_time: Mapped[str] = mapped_column(String(64))   # "10:30 AM"
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.CONFIRMED
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    booked_via: Mapped[str] = mapped_column(String(32), default="voice_agent")  # voice_agent | walk_in | online
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SMSLog(Base):
    """
    Visual demo log of SMS notifications that would be sent via Exotel in production.
    In demo mode these are just stored here; real SMS sending is toggled via EXOTEL_ENABLED.
    """
    __tablename__ = "sms_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    recipient_phone: Mapped[str] = mapped_column(String(20))
    recipient_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    message_body: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(64))  # "appointment_confirmation" | "reminder" | "cancellation"
    status: Mapped[SMSStatus] = mapped_column(Enum(SMSStatus), default=SMSStatus.DEMO)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
