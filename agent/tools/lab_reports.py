"""Viora – Lab Reports Tool."""
from agent.hms import get_hms_adapter


async def get_lab_reports(patient_id: str) -> dict:
    hms = get_hms_adapter()
    reports = await hms.get_lab_reports(patient_id)
    if not reports:
        return {"found": False, "message": "No lab reports found for this patient."}
    return {
        "found": True,
        "reports": [
            {
                "test_name": r.test_name,
                "status": r.status,
                "ordered_date": r.ordered_date.isoformat(),
                "ready_date": r.ready_date.isoformat() if r.ready_date else None,
                "result_summary": r.result_summary,
            }
            for r in reports
        ],
    }


async def get_prescriptions(patient_id: str) -> dict:
    hms = get_hms_adapter()
    rxs = await hms.get_prescriptions(patient_id)
    if not rxs:
        return {"found": False, "message": "No active prescriptions found."}
    return {
        "found": True,
        "prescriptions": [
            {
                "doctor": rx.doctor_name,
                "issued_date": rx.issued_date.isoformat(),
                "medications": rx.medications,
                "refill_allowed": rx.refill_allowed,
                "notes": rx.notes,
            }
            for rx in rxs
        ],
    }


async def get_bill_summary(patient_id: str) -> dict:
    hms = get_hms_adapter()
    bill = await hms.get_bill_summary(patient_id)
    if not bill:
        return {"found": False, "message": "No billing information found."}
    return {
        "found": True,
        "total": f"₹{bill.total_amount:,.0f}",
        "paid": f"₹{bill.paid_amount:,.0f}",
        "outstanding": f"₹{bill.outstanding:,.0f}",
        "has_balance": bill.outstanding > 0,
    }
