"""Tests for agent tools."""
import pytest


@pytest.mark.asyncio
async def test_patient_lookup_known(mock_hms):
    patient = await mock_hms.get_patient_by_phone("+919876543210")
    assert patient is not None
    assert patient.name == "Ramesh Joshi"
    assert patient.hms_id == "PT001"


@pytest.mark.asyncio
async def test_patient_lookup_unknown(mock_hms):
    patient = await mock_hms.get_patient_by_phone("+919999999999")
    assert patient is None


@pytest.mark.asyncio
async def test_available_slots_returned(mock_hms):
    slots = await mock_hms.get_available_slots()
    assert len(slots) > 0
    for slot in slots:
        assert slot.is_available is True


@pytest.mark.asyncio
async def test_book_appointment(mock_hms):
    slots = await mock_hms.get_available_slots()
    assert slots, "No slots available to book"
    slot = slots[0]
    appt = await mock_hms.book_appointment("PT001", slot.slot_id, notes="Test booking")
    assert appt.appointment_id.startswith("APT")
    assert appt.status == "scheduled"
    assert appt.patient_id == "PT001"


@pytest.mark.asyncio
async def test_book_then_cancel(mock_hms):
    slots = await mock_hms.get_available_slots()
    slot = slots[0]
    appt = await mock_hms.book_appointment("PT001", slot.slot_id)
    success = await mock_hms.cancel_appointment(appt.appointment_id)
    assert success is True


@pytest.mark.asyncio
async def test_lab_reports_known_patient(mock_hms):
    reports = await mock_hms.get_lab_reports("PT001")
    assert len(reports) >= 1
    statuses = {r.status for r in reports}
    assert statuses.issubset({"ready", "pending", "dispatched"})


@pytest.mark.asyncio
async def test_lab_reports_unknown_patient(mock_hms):
    reports = await mock_hms.get_lab_reports("PT999")
    assert reports == []


@pytest.mark.asyncio
async def test_prescriptions(mock_hms):
    rxs = await mock_hms.get_prescriptions("PT001")
    assert len(rxs) >= 1
    assert rxs[0].medications is not None


@pytest.mark.asyncio
async def test_bill_summary(mock_hms):
    bill = await mock_hms.get_bill_summary("PT001")
    assert bill is not None
    assert bill.outstanding >= 0


@pytest.mark.asyncio
async def test_new_patient_registration(mock_hms):
    pid = await mock_hms.register_new_patient_draft(
        name="Test Patient",
        phone="+919000000001",
        chief_complaint="Stomach pain",
        preferred_language="en-IN",
    )
    assert pid.startswith("PT")
    patient = await mock_hms.get_patient_by_phone("+919000000001")
    assert patient is not None
    assert patient.name == "Test Patient"


@pytest.mark.asyncio
async def test_hms_health_check(mock_hms):
    ok, latency = await mock_hms.health_check()
    assert ok is True
    assert latency >= 0
