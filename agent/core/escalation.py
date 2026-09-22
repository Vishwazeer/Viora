"""
Viora – Emergency Escalation Engine.
Monitors every transcribed utterance for red-flag keywords across EN/HI/MR.
Triggers immediate human transfer and 108 advisory when detected.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from agent.core.language_router import Lang

logger = logging.getLogger(__name__)

_KEYWORDS_PATH = Path(__file__).parent.parent.parent / "config" / "emergency_keywords.yaml"


@dataclass
class EscalationResult:
    is_emergency: bool
    matched_keywords: list[str]
    advisory_message: str
    language: Lang


def _load_keywords() -> dict[str, list[str]]:
    """Load and flatten emergency keywords from YAML into a searchable list."""
    with _KEYWORDS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    flat: dict[str, list[str]] = {}
    for lang_key in ("english", "hindi", "marathi"):
        lang_data = data.get(lang_key, {})
        all_keywords: list[str] = []
        if isinstance(lang_data, dict):
            for category_keywords in lang_data.values():
                if isinstance(category_keywords, list):
                    all_keywords.extend(category_keywords)
        flat[lang_key] = all_keywords
    return flat


_KEYWORDS = _load_keywords()

_LANG_KEY_MAP = {
    Lang.ENGLISH: "english",
    Lang.HINDI: "hindi",
    Lang.MARATHI: "marathi",
}

_ADVISORY_MESSAGES = {
    Lang.ENGLISH: (
        "I can hear that this is serious. Please call 108 immediately for emergency services. "
        "I'm connecting you to our staff right now."
    ),
    Lang.HINDI: (
        "Main samajh sakta hoon ki yeh bahut serious hai. Kripaya turant 108 pe call karein. "
        "Main abhi aapko hamare staff se connect kar raha hoon."
    ),
    Lang.MARATHI: (
        "Mala samajte ki he khup serious ahe. Krupaya turant 108 la call kara. "
        "Mi aata tumhala aamchya staff shī joḍto."
    ),
}


class EscalationEngine:
    """
    Real-time emergency detection.
    Instantiate once per call and call check() on every transcribed utterance.
    """

    def __init__(self) -> None:
        self._triggered = False

    def check(self, text: str, session_lang: Lang) -> EscalationResult:
        """
        Check an utterance for emergency keywords.
        Returns EscalationResult with is_emergency=True if a match is found.
        Once triggered, always returns emergency for the remainder of the call.
        """
        if self._triggered:
            return EscalationResult(
                is_emergency=True,
                matched_keywords=[],
                advisory_message=_ADVISORY_MESSAGES.get(session_lang, _ADVISORY_MESSAGES[Lang.ENGLISH]),
                language=session_lang,
            )

        text_lower = text.lower()
        matched: list[str] = []

        # Check keywords for all languages simultaneously (patient may code-switch in emergency)
        for _lang_key, keywords in _KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    matched.append(kw)

        if matched:
            self._triggered = True
            logger.warning("EMERGENCY DETECTED | keywords=%s | text=%r", matched, text[:100])
            return EscalationResult(
                is_emergency=True,
                matched_keywords=matched,
                advisory_message=_ADVISORY_MESSAGES.get(session_lang, _ADVISORY_MESSAGES[Lang.ENGLISH]),
                language=session_lang,
            )

        return EscalationResult(
            is_emergency=False,
            matched_keywords=[],
            advisory_message="",
            language=session_lang,
        )

    @property
    def was_triggered(self) -> bool:
        return self._triggered


def check_mental_health_crisis(text: str) -> bool:
    """Quick check specifically for mental health/self-harm language across all langs."""
    crisis_patterns = [
        r"want.{0,10}to die", r"end.{0,10}(my|this) life", r"kill.{0,5}myself",
        r"marna chahta", r"marna chahti", r"jaan dena",
        r"marayche ahe", r"jiv dyayla",
    ]
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in crisis_patterns)
