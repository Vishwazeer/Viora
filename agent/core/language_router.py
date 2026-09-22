"""
Viora – Language Router.
Detects the language of each utterance and manages the session's active language.
Sarvam STT natively handles EN/HI/MR and code-switching in one pass.
This module manages which TTS voice/language to respond in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from config.settings import get_settings

settings = get_settings()


class Lang(StrEnum):
    ENGLISH = "en-IN"
    HINDI = "hi-IN"
    MARATHI = "mr-IN"
    UNKNOWN = "unknown"


# Simple heuristic word sets for fast language detection as a fallback
# (Sarvam STT returns language_code — we use that primarily)
_HINDI_MARKERS = {
    "hai","hain","mujhe","meri","mera","aap","kya","kaise","kab","kahan",
    "theek","accha","hanji","nahi","haan","bata","chahiye","boliye","main",
    "hamara","unka","yahan","wahan","abhi","bahut","zyada","thoda",
}
_MARATHI_MARKERS = {
    "aahe","ahe","mala","majha","tumhi","kay","kasa","keva","kuthe",
    "hoy","nahi","thik","bara","sangaa","aahet","tyancha","ithe","tithe",
    "aata","khup","thoda","aamcha",
}


@dataclass
class LanguageSession:
    """Tracks language state across a single call."""
    session_lang: Lang = Lang.ENGLISH
    confidence_history: list[float] = field(default_factory=list)
    switch_count: int = 0
    low_confidence_streak: int = 0

    def update(self, detected: Lang, confidence: float) -> None:
        self.confidence_history.append(confidence)
        if confidence < 0.70:
            self.low_confidence_streak += 1
        else:
            self.low_confidence_streak = 0
            if detected != self.session_lang:
                self.session_lang = detected
                self.switch_count += 1

    @property
    def needs_clarification(self) -> bool:
        """Returns True if we've had 2+ consecutive low-confidence transcriptions."""
        return self.low_confidence_streak >= 2


def detect_language(text: str, sarvam_lang_code: str | None = None) -> tuple[Lang, float]:
    """
    Detect language from a transcribed utterance.
    Primary: use Sarvam STT's returned language code.
    Fallback: heuristic word-overlap scoring.
    """
    # Primary: trust Sarvam's detection
    if sarvam_lang_code:
        lang_map = {
            "hi": Lang.HINDI, "hi-IN": Lang.HINDI,
            "mr": Lang.MARATHI, "mr-IN": Lang.MARATHI,
            "en": Lang.ENGLISH, "en-IN": Lang.ENGLISH,
        }
        if sarvam_lang_code in lang_map:
            return lang_map[sarvam_lang_code], 0.95

    # Fallback: word-overlap heuristic
    words = set(re.sub(r"[^\w\s]", "", text.lower()).split())
    hi_score = len(words & _HINDI_MARKERS) / max(len(words), 1)
    mr_score = len(words & _MARATHI_MARKERS) / max(len(words), 1)

    if mr_score > hi_score and mr_score > 0.1:
        return Lang.MARATHI, min(mr_score * 4, 0.90)
    if hi_score > 0.1:
        return Lang.HINDI, min(hi_score * 4, 0.90)
    return Lang.ENGLISH, 0.75


def get_tts_voice_for_lang(lang: Lang) -> tuple[str, str]:
    """Return (sarvam_language_code, voice_name) for the given session language."""
    voice_map = {
        Lang.ENGLISH: ("en-IN", "meera"),
        Lang.HINDI: ("hi-IN", "pavithra"),
        Lang.MARATHI: ("mr-IN", "arvind"),
    }
    return voice_map.get(lang, ("en-IN", "meera"))


def get_filler_for_lang(lang: Lang) -> str:
    """Return a natural filler phrase for the given language (played during API latency)."""
    fillers = {
        Lang.ENGLISH: "One moment please...",
        Lang.HINDI: "Ek second...",
        Lang.MARATHI: "Ek kshan...",
    }
    return fillers.get(lang, "One moment...")
