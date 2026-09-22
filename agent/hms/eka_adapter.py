"""
Viora – Eka Care HMS Adapter.
Production adapter for the Eka Care EHR platform (https://developer.eka.care).
Requires EKA_CLIENT_ID and EKA_CLIENT_SECRET in environment.
"""

from __future__ import annotations

import time
from datetime import date, datetime

import httpx

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
from config.settings import get_settings

settings = get_settings()


class EkaCareAdapter(HMSAdapter):
    """
    Eka Care REST API adapter.
    Handles OAuth2 token lifecycle automatically (30-min access tokens).
    """

    def __init__(self) -> None:
        if not settings.EKA_CLIENT_ID or not settings.EKA_CLIENT_SECRET:
            raise OSError(
                "EKA_CLIENT_ID and EKA_CLIENT_SECRET must be set when HMS_PROVIDER=eka_care. "
                "Obtain credentials from hub.eka.care → API Tokens."
            )
        self._base = settings.EKA_BASE_URL
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._refresh_token: str | None = None
        self._client = httpx.AsyncClient(timeout=10.0)

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _ensure_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 60:
            return self._access_token
        if self._refresh_token:
            return await self._refresh()
        return await self._login()

    async def _login(self) -> str:
        resp = await self._client.post(
            f"{self._base}/auth/v1/login",
            json={"client_id": settings.EKA_CLIENT_ID, "client_secret": settings.EKA_CLIENT_SECRET},
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._token_expires_at = time.time() + data.get("expires_in", 1800)
        return self._access_token

    async def _refresh(self) -> str:
        resp = await self._client.post(
            f"{self._base}/auth/v1/refresh",
            json={"refresh_token": self._refresh_token},
        )
        if resp.status_code == 401:
            return await self._login()
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._token_expires_at = time.time() + data.get("expires_in", 1800)
        return self._access_token

    async def _get(self, path: str, **params) -> dict:
        token = await self._ensure_token()
        resp = await self._client.get(
            f"{self._base}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params={k: v for k, v in params.items() if v is not None},
        )
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, body: dict) -> dict:
        token = await self._ensure_token()
        resp = await self._client.post(
            f"{self._base}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    async def _patch(self, path: str, body: dict) -> dict:
        token = await self._ensure_token()
        resp = await self._client.patch(
            f"{self._base}{path}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Patient ───────────────────────────────────────────────────────────────

    async def get_patient_by_phone(self, phone: str) -> PatientRecord | None:
        try:
            data = await self._get("/patient/v1/search", phone=phone)
            results = data.get("patients") or data.get("data", [])
            if not results:
                return None
            return self._map_patient(results[0])
        except httpx.HTTPStatusError:
            return None

    async def get_patient_by_id(self, hms_id: str) -> PatientRecord | None:
        try:
            data = await self._get(f"/patient/v1/{hms_id}")
            return self._map_patient(data)
        except httpx.HTTPStatusError:
            return None

    async def register_new_patient_draft(self, name: str, phone: str,
                                          chief_complaint: str, preferred_language: str = "en-IN") -> str:
        parts = name.split(" ", 1)
        body = {
            "first_name": parts[0],
            "last_name": parts[1] if len(parts) > 1 else "",
            "mobile": phone,
            "chief_complaint": chief_complaint,
            "preferred_language": preferred_language,
            "status": "draft",
        }
        data = await self._post("/patient/v1/register", body)
        return data.get("patient_id") or data.get("id", "")

    def _map_patient(self, raw: dict) -> PatientRecord:
        dob = None
        if raw.get("date_of_birth"):
            try:
                dob = date.fromisoformat(raw["date_of_birth"])
            except ValueError:
                pass
        last_visit = None
        if raw.get("last_visit"):
            try:
                last_visit = date.fromisoformat(raw["last_visit"][:10])
            except ValueError:
                pass
        return PatientRecord(
            hms_id=str(raw.get("id") or raw.get("patient_id", "")),
            name=f"{raw.get('first_name','')} {raw.get('last_name','')}".strip(),
            phone=raw.get("mobile") or raw.get("phone", ""),
            date_of_birth=dob,
            gender=raw.get("gender"),
            blood_group=raw.get("blood_group"),
            email=raw.get("email"),
            address=raw.get("address"),
            last_visit=last_visit,
            preferred_language=raw.get("preferred_language", "en-IN"),
        )

    # ── Appointments ──────────────────────────────────────────────────────────

    async def get_available_slots(self, doctor_id: str | None = None,
                                   department: str | None = None,
                                   preferred_date: date | None = None) -> list[TimeSlot]:
        params: dict = {}
        if doctor_id:
            params["doctorId"] = doctor_id
        if department:
            params["department"] = department
        if preferred_date:
            params["date"] = preferred_date.isoformat()
        data = await self._get("/scheduling/v1/slots", **params)
        slots_raw = data.get("slots") or data.get("data", [])
        result = []
        for s in slots_raw[:8]:
            start = datetime.fromisoformat(s["start_time"])
            end = datetime.fromisoformat(s["end_time"])
            result.append(TimeSlot(
                slot_id=str(s["slot_id"]),
                doctor_id=str(s["doctor_id"]),
                doctor_name=s.get("doctor_name", ""),
                start_time=start,
                end_time=end,
                is_available=s.get("is_available", True),
            ))
        return result

    async def book_appointment(self, patient_id: str, slot_id: str,
                                notes: str | None = None) -> Appointment:
        body = {"patient_id": patient_id, "slot_id": slot_id}
        if notes:
            body["notes"] = notes
        data = await self._post("/scheduling/v1/appointments", body)
        return self._map_appointment(data)

    async def cancel_appointment(self, appointment_id: str, reason: str | None = None) -> bool:
        body = {"status": "cancelled"}
        if reason:
            body["cancellation_reason"] = reason
        try:
            await self._patch(f"/scheduling/v1/appointments/{appointment_id}", body)
            return True
        except httpx.HTTPStatusError:
            return False

    async def reschedule_appointment(self, appointment_id: str, new_slot_id: str) -> Appointment:
        data = await self._patch(f"/scheduling/v1/appointments/{appointment_id}",
                                  {"slot_id": new_slot_id, "status": "rescheduled"})
        return self._map_appointment(data)

    async def get_patient_appointments(self, patient_id: str, upcoming_only: bool = True) -> list[Appointment]:
        params: dict = {"patientId": patient_id}
        if upcoming_only:
            params["fromDate"] = datetime.now().isoformat()
            params["status"] = "scheduled"
        data = await self._get("/scheduling/v1/appointments", **params)
        raw = data.get("appointments") or data.get("data", [])
        return [self._map_appointment(a) for a in raw]

    def _map_appointment(self, raw: dict) -> Appointment:
        return Appointment(
            appointment_id=str(raw.get("appointment_id") or raw.get("id", "")),
            patient_id=str(raw.get("patient_id", "")),
            doctor_id=str(raw.get("doctor_id", "")),
            doctor_name=raw.get("doctor_name", ""),
            department=raw.get("department", ""),
            appointment_time=datetime.fromisoformat(raw["appointment_time"]),
            status=raw.get("status", "scheduled"),
            notes=raw.get("notes"),
        )

    # ── Doctors ───────────────────────────────────────────────────────────────

    async def list_doctors(self, department: str | None = None) -> list[Doctor]:
        params = {"department": department} if department else {}
        data = await self._get("/provider/v1/doctors", **params)
        raw = data.get("doctors") or data.get("data", [])
        return [Doctor(
            hms_id=str(d.get("id","")),
            name=d.get("name",""),
            specialisation=d.get("specialisation",""),
            department=d.get("department",""),
            available_days=d.get("available_days",[]),
            consultation_fee=d.get("consultation_fee"),
        ) for d in raw]

    # ── Lab Reports ───────────────────────────────────────────────────────────

    async def get_lab_reports(self, patient_id: str) -> list[LabReport]:
        data = await self._get("/lab/v1/reports", patientId=patient_id)
        raw = data.get("reports") or data.get("data", [])
        result = []
        for r in raw:
            ordered = date.fromisoformat(r["ordered_date"][:10]) if r.get("ordered_date") else date.today()
            ready = date.fromisoformat(r["ready_date"][:10]) if r.get("ready_date") else None
            result.append(LabReport(
                report_id=str(r.get("report_id","")),
                patient_id=patient_id,
                test_name=r.get("test_name",""),
                ordered_date=ordered,
                status=r.get("status","pending"),
                result_summary=r.get("result_summary"),
                ready_date=ready,
            ))
        return result

    # ── Prescriptions ─────────────────────────────────────────────────────────

    async def get_prescriptions(self, patient_id: str) -> list[Prescription]:
        data = await self._get("/emr/v1/prescriptions", patientId=patient_id)
        raw = data.get("prescriptions") or data.get("data", [])
        result = []
        for p in raw:
            issued = date.fromisoformat(p["issued_date"][:10]) if p.get("issued_date") else date.today()
            result.append(Prescription(
                prescription_id=str(p.get("id","")),
                patient_id=patient_id,
                doctor_name=p.get("doctor_name",""),
                issued_date=issued,
                medications=p.get("medications",[]),
                notes=p.get("notes"),
                refill_allowed=p.get("refill_allowed",False),
            ))
        return result

    # ── Billing ───────────────────────────────────────────────────────────────

    async def get_bill_summary(self, patient_id: str) -> BillSummary | None:
        try:
            data = await self._get("/billing/v1/summary", patientId=patient_id)
            return BillSummary(
                bill_id=str(data.get("bill_id","")),
                patient_id=patient_id,
                total_amount=float(data.get("total_amount",0)),
                paid_amount=float(data.get("paid_amount",0)),
                outstanding=float(data.get("outstanding",0)),
            )
        except httpx.HTTPStatusError:
            return None

    # ── Health Check ──────────────────────────────────────────────────────────

    async def health_check(self) -> tuple[bool, int]:
        start = time.monotonic()
        try:
            await self._ensure_token()
            latency = int((time.monotonic() - start) * 1000)
            return True, latency
        except Exception:
            return False, -1
