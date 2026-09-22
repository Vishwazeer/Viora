"""
Viora – Sentiment Monitor.
Detects caller stress, frustration, or distress in real-time.
Signals the pipeline to respond empathetically.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SentimentResult:
    score: float        # -1.0 (very negative) to +1.0 (very positive)
    is_stressed: bool
    is_frustrated: bool
    empathy_phrase: str | None  # inject this before next response if stressed


_FRUSTRATION_EN = {
    "useless", "stupid", "ridiculous", "waste", "rubbish", "nonsense",
    "not working", "this is bad", "i'm angry", "pathetic", "joke",
    "nobody listens", "no one helps", "fed up", "done with this",
}
_FRUSTRATION_HI = {
    "bakwaas", "bekar", "faltu", "ganda", "pareshan", "gussa",
    "naraaz", "tang", "kuch kaam nahi", "koi nahi sunta",
}
_FRUSTRATION_MR = {
    "bekar", "chukichuk", "ragavto", "trasta", "vait",
    "kuni aikt nahi", "kaam nahi karto",
}

_STRESS_SIGNALS = {
    "please", "urgent", "quick", "fast", "hurry", "emergency",
    "jaldi", "please please", "kripaya", "ghabrayo", "tavar",
    "turant", "please jaldi",
}

_POSITIVE_EN = {"thank", "great", "perfect", "wonderful", "helpful", "excellent"}

_EMPATHY_PHRASES: dict[str, str] = {
    "en-IN": "I completely understand, and I'm sorry you're going through this. Let me help you right now.",
    "hi-IN": "Main bilkul samajh sakta hoon, aur mujhe afsos hai. Aao main abhi aapki madad karta hoon.",
    "mr-IN": "Mala poorna samajhte ahe, ani mala vaeet vaatte. Aata mi tumhala lagech madad karto.",
}


class SentimentMonitor:
    """
    Lightweight rule-based sentiment tracker.
    Accumulates signal across the call to detect escalating frustration.
    """

    def __init__(self) -> None:
        self._frustration_signal: float = 0.0
        self._running_score: float = 0.0
        self._sample_count: int = 0

    def analyse(self, text: str, session_lang: str = "en-IN") -> SentimentResult:
        text_lower = text.lower()
        words = set(re.sub(r"[^\w\s]", "", text_lower).split())

        # Score frustration markers
        fr_en = len(words & _FRUSTRATION_EN)
        fr_hi = len(words & _FRUSTRATION_HI)
        fr_mr = len(words & _FRUSTRATION_MR)
        frustration_hit = (fr_en + fr_hi + fr_mr) > 0

        # Score stress signals
        stress_hit = any(s in text_lower for s in _STRESS_SIGNALS)

        # Score positive signals
        positive_hit = any(p in text_lower for p in _POSITIVE_EN)

        # Running score update
        if frustration_hit:
            self._frustration_signal += 0.4
            self._running_score -= 0.3
        elif stress_hit:
            self._running_score -= 0.15
        elif positive_hit:
            self._running_score += 0.2
            self._frustration_signal = max(0.0, self._frustration_signal - 0.1)

        self._sample_count += 1
        score = max(-1.0, min(1.0, self._running_score / max(self._sample_count, 1) * 3))

        is_frustrated = self._frustration_signal >= 0.4
        is_stressed = stress_hit and not frustration_hit

        empathy: str | None = None
        if is_frustrated or is_stressed:
            empathy = _EMPATHY_PHRASES.get(session_lang, _EMPATHY_PHRASES["en-IN"])

        return SentimentResult(
            score=round(score, 3),
            is_stressed=is_stressed,
            is_frustrated=is_frustrated,
            empathy_phrase=empathy,
        )

    @property
    def overall_score(self) -> float:
        return max(-1.0, min(1.0, self._running_score / max(self._sample_count, 1) * 3))
