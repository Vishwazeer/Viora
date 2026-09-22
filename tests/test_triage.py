"""Tests for the symptom triage engine."""
from agent.tools.triage import score_triage


def test_low_risk_triage():
    result = score_triage("mild headache", ["headache"], "2 days", severity=2)
    assert result.risk_level in ("low", "medium")
    assert result.risk_score < 60


def test_high_risk_triage():
    result = score_triage("chest pain", ["chest pain", "shortness of breath"], "today", severity=9)
    assert result.risk_level in ("high", "emergency")
    assert result.risk_score >= 50


def test_emergency_red_flag():
    result = score_triage(
        "sudden severe headache", ["severe headache", "face drooping", "arm weakness"],
        "minutes", severity=10
    )
    assert result.risk_level == "emergency"
    assert len(result.red_flags_detected) > 0


def test_recommended_action_present():
    result = score_triage("stomach pain", ["stomach ache"], "3 days", severity=4)
    assert len(result.recommended_action) > 10


def test_elderly_factor():
    young = score_triage("mild cough", ["cough"], "1 week", severity=2, patient_age=30)
    elderly = score_triage("mild cough", ["cough"], "1 week", severity=2, patient_age=75)
    assert elderly.risk_score >= young.risk_score


def test_score_capped_at_100():
    result = score_triage("emergency", ["chest pain", "stroke", "unconscious"], "now", severity=10)
    assert result.risk_score <= 100
