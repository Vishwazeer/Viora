import asyncio

from agent.core.escalation import EscalationEngine
from agent.core.language_router import Lang, LanguageRouter
from agent.hms.mock_adapter import MockHMSAdapter
from agent.tools.triage import score_triage
from config.settings import get_settings

s = get_settings()
print(f"Settings OK — HMS={s.HMS_PROVIDER}, env={s.ENVIRONMENT}")

hms = MockHMSAdapter()
async def check():
    patient = await hms.get_patient_by_phone("+919876543210")
    print(f"Mock HMS OK — patient={patient.name}")
    slots = await hms.get_available_slots()
    print(f"Slots OK — {len(slots)} available")
asyncio.run(check())

engine = EscalationEngine()

r = engine.check("chest pain", Lang.ENGLISH)
print(f"Escalation OK — is_emergency={r.is_emergency}")

lr = LanguageRouter()
lang = lr.detect("hello I need an appointment")
print(f"Language Router OK — detected={lang}")

tr = score_triage("headache", ["headache"], "2 days", severity=3)
print(f"Triage OK — risk={tr.risk_level}, score={tr.risk_score}")

print("\n=== ALL BACKEND CHECKS PASSED ===")
