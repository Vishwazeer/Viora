"""
Viora – Dialogue Manager.
Manages multi-turn conversation state: slot filling, clarification tracking,
and context memory within a single call session.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agent.core.language_router import Lang


class Intent(StrEnum):
    APPOINTMENT_BOOK = "appointment_book"
    APPOINTMENT_CANCEL = "appointment_cancel"
    APPOINTMENT_RESCHEDULE = "appointment_reschedule"
    DOCTOR_AVAILABILITY = "doctor_availability"
    OPD_TIMINGS = "opd_timings"
    LAB_REPORT = "lab_report"
    PRESCRIPTION = "prescription"
    SYMPTOM_TRIAGE = "symptom_triage"
    REGISTRATION = "registration"
    BILLING = "billing"
    INSURANCE = "insurance"
    FAQ = "faq"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


@dataclass
class Turn:
    """Represents one exchange in the conversation."""
    role: str         # "user" | "assistant"
    text: str
    language: Lang
    intent: Intent | None = None
    tool_called: str | None = None
    timestamp_ms: int = 0


@dataclass
class DialogueState:
    """
    Complete in-memory state for one call session.
    Passed around all agent components to maintain context.
    """
    call_id: str
    patient_id: str | None = None
    patient_name: str | None = None
    patient_phone: str = ""
    session_lang: Lang = Lang.ENGLISH
    is_known_patient: bool = False

    # Conversation history (for LLM context window)
    turns: list[Turn] = field(default_factory=list)

    # Slot filling state
    current_intent: Intent = Intent.UNKNOWN
    collected_slots: dict[str, Any] = field(default_factory=dict)
    pending_slots: list[str] = field(default_factory=list)

    # Meta
    clarification_count: int = 0
    consent_given: bool = False
    escalated: bool = False
    escalation_reason: str | None = None
    turn_count: int = 0

    def add_turn(self, role: str, text: str, intent: Intent | None = None,
                 tool_called: str | None = None) -> None:
        self.turns.append(Turn(
            role=role, text=text, language=self.session_lang,
            intent=intent, tool_called=tool_called,
        ))
        if role == "user":
            self.turn_count += 1

    def set_intent(self, intent: Intent) -> None:
        if intent != self.current_intent:
            self.current_intent = intent
            self.collected_slots.clear()
            self.pending_slots.clear()
            self.clarification_count = 0

    def set_slot(self, key: str, value: Any) -> None:
        self.collected_slots[key] = value
        if key in self.pending_slots:
            self.pending_slots.remove(key)

    def needs_slot(self, key: str) -> bool:
        return key not in self.collected_slots

    def get_context_for_llm(self, max_turns: int = 12) -> list[dict]:
        """Return last N turns formatted for the Gemini chat API."""
        recent = self.turns[-max_turns:]
        return [{"role": t.role, "parts": [{"text": t.text}]} for t in recent]

    @property
    def needs_escalation(self) -> bool:
        return self.clarification_count >= 3


class DialogueManager:
    """Manages dialogue flow, slot requirements, and clarification logic."""

    # Slots required per intent
    _REQUIRED_SLOTS: dict[Intent, list[str]] = {
        Intent.APPOINTMENT_BOOK: ["preferred_date", "department_or_doctor"],
        Intent.APPOINTMENT_CANCEL: ["appointment_id_or_date"],
        Intent.APPOINTMENT_RESCHEDULE: ["appointment_id_or_date", "new_preferred_date"],
        Intent.SYMPTOM_TRIAGE: ["chief_complaint", "duration", "severity"],
        Intent.REGISTRATION: ["patient_name", "chief_complaint"],
    }

    def __init__(self, state: DialogueState) -> None:
        self.state = state

    def handle_clarification_failure(self) -> str:
        """Called when the agent can't understand after N attempts."""
        self.state.clarification_count += 1
        if self.state.needs_escalation:
            self.state.escalated = True
            self.state.escalation_reason = "max_clarifications"
            return self._escalation_message()
        return self._try_again_message()

    def get_next_missing_slot_prompt(self) -> str | None:
        """Return a natural-language prompt for the next unfilled required slot."""
        required = self._REQUIRED_SLOTS.get(self.state.current_intent, [])
        for slot in required:
            if self.state.needs_slot(slot):
                return _SLOT_PROMPTS.get(self.state.session_lang, {}).get(slot)
        return None

    def _escalation_message(self) -> str:
        msgs = {
            Lang.ENGLISH: "I'm sorry I wasn't able to help you fully. Let me connect you to our team right away.",
            Lang.HINDI: "Mujhe maafi chahiye, main aapki poori tarah se madad nahi kar paya. Main abhi aapko hamare team se connect karta hoon.",
            Lang.MARATHI: "Mala maafi asha ki mi tumchi poorna madad karu shaklo nahi. Mi aata tumhala aamchya teamshī joḍto.",
        }
        return msgs.get(self.state.session_lang, msgs[Lang.ENGLISH])

    def _try_again_message(self) -> str:
        msgs = {
            Lang.ENGLISH: "I'm sorry, I didn't quite catch that. Could you say that again?",
            Lang.HINDI: "Maafi kijiye, main samajh nahi paya. Kya aap dobara bol sakte hain?",
            Lang.MARATHI: "Kshama kara, mala samajle nahi. Ka tumhi parat sangaal ka?",
        }
        return msgs.get(self.state.session_lang, msgs[Lang.ENGLISH])


# Slot prompt templates per language
_SLOT_PROMPTS: dict[Lang, dict[str, str]] = {
    Lang.ENGLISH: {
        "preferred_date": "Which date works best for you? You can say something like 'this Friday' or 'next Monday'.",
        "department_or_doctor": "Which department or doctor would you like to see?",
        "appointment_id_or_date": "Could you tell me the date of the appointment you'd like to change?",
        "new_preferred_date": "And what new date would you prefer?",
        "chief_complaint": "Could you tell me briefly what you're experiencing?",
        "duration": "How long have you been experiencing this?",
        "severity": "On a scale of 1 to 10, how severe is the discomfort?",
        "patient_name": "Could I have your full name, please?",
    },
    Lang.HINDI: {
        "preferred_date": "Aapko kaunsa din theek rahega? Aap keh sakte hain jaise 'is shukravar' ya 'agle somvar'.",
        "department_or_doctor": "Aap kis doctor ya department mein milna chahte hain?",
        "appointment_id_or_date": "Aap kaunsi appointment badalna chahte hain, uski tarikh bata sakte hain?",
        "new_preferred_date": "Naya din kab chahiye aapko?",
        "chief_complaint": "Aap kya takleef feel kar rahe hain, zara bataiye?",
        "duration": "Yeh takleef kitne samay se hai?",
        "severity": "1 se 10 tak bole toh kitna dard hai?",
        "patient_name": "Kripaya apna poora naam bataiye.",
    },
    Lang.MARATHI: {
        "preferred_date": "Tumhala konti tarikh yogya ahe? Tumhi mhanu shakta 'ya shukravar' kinva 'pudcha somvar'.",
        "department_or_doctor": "Tumhala konyaa doctor kiva department madhye bhety ghyayachi ahe?",
        "appointment_id_or_date": "Tumhala konti appointment badlaayachi ahe tiche tarikh sangal ka?",
        "new_preferred_date": "Navi tarikh kevi pahije?",
        "chief_complaint": "Tumhala kay tras hot ahe te sangal ka?",
        "duration": "He kitpasun hot ahe?",
        "severity": "1 to 10 var sangal tar kitka tras ahe?",
        "patient_name": "Krupaya tumche poorne naav sangaa.",
    },
}
