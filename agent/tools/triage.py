"""
Viora – Symptom Triage Tool.
Structured ICMR-aligned symptom intake with risk scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "prompts.yaml"


def _load_red_flags() -> list[str]:
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("triage", {}).get("red_flag_symptoms", [])


_RED_FLAGS = _load_red_flags()
_EMERGENCY_THRESHOLD = 80
_URGENT_THRESHOLD = 50


@dataclass
class TriageResult:
    chief_complaint: str
    symptoms: list[str]
    duration: str
    severity: int           # 1-10
    risk_level: str         # low | medium | high | emergency
    risk_score: int         # 0-100
    recommended_action: str
    red_flags_detected: list[str] = field(default_factory=list)


def score_triage(
    chief_complaint: str,
    symptoms: list[str],
    duration: str,
    severity: int,
    patient_age: int | None = None,
) -> TriageResult:
    """
    Compute a risk score using a simplified ICMR-aligned algorithm.
    Inputs come from slot-filling across the conversation.
    """
    score = 0
    red_flags: list[str] = []

    # Severity weight (primary driver)
    score += severity * 6  # max 60 points

    # Red-flag symptom detection
    all_text = f"{chief_complaint} {' '.join(symptoms)}".lower()
    for flag in _RED_FLAGS:
        if flag.lower() in all_text:
            red_flags.append(flag)
            score += 20
            break  # one red flag is enough to push to high risk

    # Duration – acute symptoms score higher
    duration_lower = duration.lower()
    if any(w in duration_lower for w in ["today", "minutes", "hours", "aaj", "abhi", "turant"]):
        score += 15
    elif any(w in duration_lower for w in ["days", "din", "din se"]):
        score += 8

    # Age factor
    if patient_age and (patient_age < 5 or patient_age > 65):
        score += 10

    score = min(score, 100)

    if score >= _EMERGENCY_THRESHOLD or red_flags:
        risk_level = "emergency"
        action = (
            "This sounds like an emergency. Please call 108 immediately or go to the "
            "nearest emergency room. Our doctor will be informed right away."
        )
    elif score >= _URGENT_THRESHOLD:
        risk_level = "high"
        action = (
            "Your symptoms need prompt attention. I strongly recommend you visit the clinic today "
            "or call us back to schedule an urgent appointment."
        )
    elif score >= 25:
        risk_level = "medium"
        action = "Please schedule an appointment within the next 2-3 days for a proper evaluation."
    else:
        risk_level = "low"
        action = "Your symptoms appear mild at this time. Monitor them and schedule a routine appointment."

    return TriageResult(
        chief_complaint=chief_complaint,
        symptoms=symptoms,
        duration=duration,
        severity=severity,
        risk_level=risk_level,
        risk_score=score,
        recommended_action=action,
        red_flags_detected=red_flags,
    )


async def run_triage(
    chief_complaint: str,
    symptoms: list[str],
    duration: str,
    severity: int,
    patient_age: int | None = None,
) -> dict:
    """Tool entry-point: run triage and return a serialisable result."""
    result = score_triage(chief_complaint, symptoms, duration, severity, patient_age)
    return {
        "risk_level": result.risk_level,
        "risk_score": result.risk_score,
        "recommended_action": result.recommended_action,
        "red_flags": result.red_flags_detected,
        "is_emergency": result.risk_level == "emergency",
    }
