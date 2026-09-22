"""Viora – New Patient Registration Tool."""
from agent.hms import get_hms_adapter


async def register_new_patient(
    name: str,
    phone: str,
    chief_complaint: str,
    preferred_language: str = "en-IN",
) -> dict:
    """Create a draft new patient record in the HMS."""
    hms = get_hms_adapter()
    try:
        patient_id = await hms.register_new_patient_draft(
            name=name,
            phone=phone,
            chief_complaint=chief_complaint,
            preferred_language=preferred_language,
        )
        return {
            "success": True,
            "patient_id": patient_id,
            "message": (
                f"Your registration has been submitted successfully. "
                f"Your patient reference is {patient_id}. "
                f"Our team will confirm your details and reach out to you."
            ),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Registration could not be completed at this time. Error: {e}",
        }
