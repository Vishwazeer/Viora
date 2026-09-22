"""Tests for the emergency escalation engine."""
from agent.core.escalation import EscalationEngine, check_mental_health_crisis
from agent.core.language_router import Lang


def test_english_emergency_detected():
    engine = EscalationEngine()
    result = engine.check("I have severe chest pain", Lang.ENGLISH)
    assert result.is_emergency is True
    assert "chest pain" in result.matched_keywords


def test_hindi_emergency_detected():
    engine = EscalationEngine()
    result = engine.check("mujhe seene mein dard ho raha hai", Lang.HINDI)
    assert result.is_emergency is True


def test_marathi_emergency_detected():
    engine = EscalationEngine()
    result = engine.check("mala chhati mein vedna hoti ahe", Lang.MARATHI)
    assert result.is_emergency is True


def test_no_false_positive_appointment():
    engine = EscalationEngine()
    result = engine.check("I want to book an appointment for next Monday", Lang.ENGLISH)
    assert result.is_emergency is False


def test_once_triggered_stays_triggered():
    engine = EscalationEngine()
    engine.check("chest pain emergency", Lang.ENGLISH)
    assert engine.was_triggered is True
    result2 = engine.check("never mind I'm okay", Lang.ENGLISH)
    assert result2.is_emergency is True  # stays triggered


def test_advisory_message_not_empty():
    engine = EscalationEngine()
    result = engine.check("I can't breathe", Lang.ENGLISH)
    if result.is_emergency:
        assert len(result.advisory_message) > 20


def test_mental_health_crisis_english():
    assert check_mental_health_crisis("I want to end my life") is True


def test_mental_health_crisis_hindi():
    assert check_mental_health_crisis("main marna chahta hun") is True


def test_mental_health_no_false_positive():
    assert check_mental_health_crisis("I want to book an appointment") is False


def test_language_advisory_matches_session():
    engine = EscalationEngine()
    result_hi = engine.check("seene mein dard", Lang.HINDI)
    if result_hi.is_emergency:
        assert "108" in result_hi.advisory_message
