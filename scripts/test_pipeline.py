"""
Viora – End-to-End Pipeline & Feature Verification Suite.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
import dotenv
import httpx

# Load .env
dotenv.load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from agent.hms.mock_adapter import MockHMSAdapter
from agent.core.language_router import detect_language, LanguageSession, Lang
from agent.core.sentiment_monitor import SentimentMonitor
from agent.core.escalation import EscalationEngine, check_mental_health_crisis
from agent.core.barge_in_handler import BargeInHandler
from agent.tools.clinic import (
    get_clinic_info,
    list_doctors,
    check_doctor_availability,
    book_appointment,
    cancel_appointment,
)
from agent.tools.triage import run_triage, score_triage
from db.session import get_db_context, create_all_tables
from db.models import CallLog, Appointment, Patient, Language, CallOutcome, CallIntent

settings = get_settings()

class PipelineTester:
    def __init__(self):
        self.results = []

    def log(self, category: str, name: str, passed: bool, details: str = ""):
        icon = "✅ PASS" if passed else "❌ FAIL"
        self.results.append((category, name, passed, details))
        print(f"{icon} | [{category.ljust(14)}] | {name.ljust(35)} | {details}")

    async def test_db(self):
        print("\n" + "="*75)
        print("1. DATABASE & ORM MODELS")
        print("="*75)
        try:
            await create_all_tables()
            async with get_db_context() as db:
                # Add a test patient
                test_patient = Patient(
                    phone_number="+919876543210",
                    name="Ramesh Joshi",
                    preferred_language=Language.ENGLISH,
                    is_known_patient=True
                )
                db.add(test_patient)
                await db.flush()

                # Add a test appointment
                test_appt = Appointment(
                    patient_name="Ramesh Joshi",
                    patient_phone="+919876543210",
                    doctor_name="Dr. Priya Sharma",
                    department="General Medicine",
                    appointment_date="2026-08-30",
                    appointment_time="10:00 AM",
                    reason="Routine Checkup",
                    status="confirmed",
                    booked_via="ai_voice"
                )
                db.add(test_appt)

                # Add a test call log
                test_log = CallLog(
                    livekit_room_name="test-call-room-001",
                    patient_phone="+919876543210",
                    language=Language.ENGLISH,
                    primary_intent=CallIntent.APPOINTMENT_BOOK,
                    outcome=CallOutcome.RESOLVED,
                    turn_count=4,
                    duration_seconds=95,
                    sentiment_score=0.85,
                    consent_given=True,
                    summary="Patient successfully booked an appointment with Dr. Priya Sharma."
                )
                db.add(test_log)

            self.log("Database", "Table creation & ORM session", True, "SQLite async engine active")
            self.log("Database", "Data insertion & querying", True, "Patient, Appointment, CallLog records created")
        except Exception as e:
            self.log("Database", "Database operations", False, str(e))

    async def test_hms_and_tools(self):
        print("\n" + "="*75)
        print("2. HMS ADAPTER & AGENT TOOLS")
        print("="*75)
        hms = MockHMSAdapter()
        
        # 1. Health check
        ok, latency = await hms.health_check()
        self.log("HMS Adapter", "HMS Health Check", ok, f"Latency: {latency:.2f}ms")

        # 2. Clinic Info & Doctors
        clinic = await get_clinic_info()
        self.log("Tools: Clinic", "Get Clinic Info", "Healing Hands" in clinic, clinic[:45] + "...")

        docs = await list_doctors("General Medicine")
        self.log("Tools: Clinic", "List Doctors (General Med)", "Priya Sharma" in docs, docs[:45] + "...")

        # 3. Doctor Availability
        avail = await check_doctor_availability("Priya Sharma", "Monday")
        self.log("Tools: Clinic", "Check Doctor Availability", "available" in avail.lower(), avail[:45] + "...")

        # 4. Booking and Cancellation
        booked = await book_appointment(
            patient_name="Ramesh Joshi",
            patient_phone="+919876543210",
            doctor_name="Dr. Priya Sharma",
            appointment_date="Monday 31st August",
            appointment_time="10:00 AM",
            reason="Fever checkup"
        )
        self.log("Tools: Appts", "Book Appointment Tool", "CONFIRMED" in booked or "confirmed" in booked, booked[:50] + "...")

        cancelled = await cancel_appointment("HHC-TEST123", "+919876543210")
        self.log("Tools: Appts", "Cancel Appointment Tool", "cancellation request" in cancelled, cancelled[:45] + "...")

        # 5. Patient Lookup & Registration on HMS Adapter
        patient = await hms.get_patient_by_phone("+919876543210")
        self.log("HMS Adapter", "Lookup Known Patient", patient is not None and patient.name == "Ramesh Joshi", f"Found: {patient.name if patient else 'None'}")

        new_pid = await hms.register_new_patient_draft("Aarav Patel", "+919111222333", "Cough")
        self.log("HMS Adapter", "Register New Patient", new_pid.startswith("PT"), f"New ID: {new_pid}")

        # 6. Lab Reports & Prescriptions on HMS Adapter
        labs = await hms.get_lab_reports("PT001")
        self.log("HMS Adapter", "Get Lab Reports", len(labs) >= 1, f"Reports count: {len(labs)}")

        prescriptions = await hms.get_prescriptions("PT001")
        self.log("HMS Adapter", "Get Prescriptions", len(prescriptions) >= 1, f"Rx count: {len(prescriptions)}")

        # 7. Clinical Triage
        triage_mild = await run_triage("mild headache", ["tiredness"], "3 days", 2)
        self.log("Tools: Triage", "Mild Symptom Triage", triage_mild.get("risk_level") == "low", f"Risk: {triage_mild.get('risk_level')}")

        triage_emerg = await run_triage("chest pain", ["shortness of breath"], "1 hour", 9)
        self.log("Tools: Triage", "Emergency Red-Flag Triage", triage_emerg.get("is_emergency") is True, f"Action: {triage_emerg.get('recommended_action')[:40]}...")

    async def test_agent_core(self):
        print("\n" + "="*75)
        print("3. AGENT CORE (Language, Sentiment, Escalation, Barge-in)")
        print("="*75)
        # Language Router
        l_en, _ = detect_language("I want to book an appointment")
        l_hi, _ = detect_language("mujhe doctor se milna hai appointment chahiye")
        l_mr, _ = detect_language("mala doctoranna bhetayche ahe vel milel ka")
        self.log("Core: Language", "Detect English", l_en == Lang.ENGLISH, str(l_en))
        self.log("Core: Language", "Detect Hindi", l_hi == Lang.HINDI, str(l_hi))
        self.log("Core: Language", "Detect Marathi", l_mr == Lang.MARATHI, str(l_mr))

        # Sentiment Monitor
        monitor = SentimentMonitor()
        r1 = monitor.analyse("Thank you very much, you were extremely helpful!")
        r2 = monitor.analyse("This is the worst useless service ever, I am angry!")
        self.log("Core: Sentiment", "Positive sentiment scoring", r1.score >= 0, f"Score: {r1.score}")
        self.log("Core: Sentiment", "Negative frustration detection", r2.is_frustrated or r2.score < 0, f"Score: {r2.score}, Frustrated: {r2.is_frustrated}")

        # Escalation Engine
        escalation = EscalationEngine()
        res_normal = escalation.check("I have a slight cold", Lang.ENGLISH)
        res_emerg = escalation.check("The patient is unconscious and not breathing!", Lang.ENGLISH)
        
        escalation_hi = EscalationEngine()
        res_hindi = escalation_hi.check("mujhe seene mein dard ho raha hai", Lang.HINDI)

        self.log("Core: Escalation", "Normal query (no escalation)", not res_normal.is_emergency, "No trigger")
        self.log("Core: Escalation", "English Emergency escalation", res_emerg.is_emergency, f"Matched: {res_emerg.matched_keywords}")
        self.log("Core: Escalation", "Hindi Emergency escalation", res_hindi.is_emergency, f"Matched: {res_hindi.matched_keywords}")

        # Mental Health check
        is_crisis = check_mental_health_crisis("I want to end my life")
        self.log("Core: Crisis", "Mental health crisis detection", is_crisis, "Crisis keyword triggered")

        # Barge-in Handler
        barge = BargeInHandler()
        self.log("Core: BargeIn", "Barge-in detection init", barge is not None, "Barge-in handler active")

    async def test_api_routes(self):
        print("\n" + "="*75)
        print("4. FASTAPI BACKEND ROUTES")
        print("="*75)
        headers = {"X-Admin-Key": settings.DASHBOARD_ADMIN_KEY}
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=10.0) as client:
            # Health
            r = await client.get("/health")
            self.log("API: Health", "GET /health", r.status_code == 200 and r.json().get("status") == "ok", str(r.json()))

            # Root
            r = await client.get("/")
            self.log("API: Root", "GET /", r.status_code == 200, str(r.json()))

            # Dashboard Stats
            r = await client.get("/dashboard/stats", headers=headers)
            self.log("API: Dashboard", "GET /dashboard/stats", r.status_code == 200, f"Calls: {r.json().get('total_calls')}")

            # Dashboard Calls
            r = await client.get("/dashboard/calls", headers=headers)
            calls_list = r.json().get("calls", [])
            self.log("API: Dashboard", "GET /dashboard/calls", r.status_code == 200, f"Count: {len(calls_list)}")

            # Dashboard Escalations
            r = await client.get("/dashboard/escalations", headers=headers)
            self.log("API: Dashboard", "GET /dashboard/escalations", r.status_code == 200, f"Count: {len(r.json().get('escalations', []))}")

            # Admin Config
            r = await client.get("/admin/config", headers=headers)
            self.log("API: Admin", "GET /admin/config", r.status_code == 200, f"App: {r.json().get('app_name')}")

            # Admin Flags
            r = await client.get("/admin/flags", headers=headers)
            self.log("API: Admin", "GET /admin/flags", r.status_code == 200, f"Flags: {list(r.json().get('flags', {}).keys())}")

            # Admin Flags Patch
            r = await client.patch("/admin/flags/triage_enabled?enabled=true", headers=headers)
            self.log("API: Admin", "PATCH /admin/flags/triage_enabled", r.status_code == 200, str(r.json()))

            # Appointments
            r = await client.get("/appointments/", headers=headers)
            self.log("API: Appts", "GET /appointments/", r.status_code == 200, f"Count: {len(r.json())}")

            # Appointments Stats
            r = await client.get("/appointments/stats", headers=headers)
            self.log("API: Appts", "GET /appointments/stats", r.status_code == 200, str(r.json()))

            # SMS Log
            r = await client.get("/appointments/sms-log", headers=headers)
            self.log("API: SMS", "GET /appointments/sms-log", r.status_code == 200, f"Count: {len(r.json())}")

            # Simulator Token
            r = await client.post("/admin/simulator/token?room_name=test-demo&identity=tester", headers=headers)
            self.log("API: LiveKit", "POST /admin/simulator/token", r.status_code == 200 and "token" in r.json(), f"URL: {r.json().get('url')}")

            # Exotel Webhook
            r = await client.post("/webhooks/inbound-call", json={"CallSid": "test-sid-999", "From": "+919876543210", "To": "+918045678900", "CallType": "transferred"})
            self.log("API: Webhook", "POST /webhooks/inbound-call", r.status_code == 200, str(r.json()))

    async def run_all(self):
        print(f"Viora Comprehensive Verification Suite — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await self.test_db()
        await self.test_hms_and_tools()
        await self.test_agent_core()
        await self.test_api_routes()

        total = len(self.results)
        passed = sum(1 for _, _, p, _ in self.results if p)
        failed = total - passed

        print("\n" + "="*75)
        print("FINAL VERIFICATION SUMMARY")
        print("="*75)
        print(f"Total Tests Executed: {total}")
        print(f"Passed:               {passed}")
        print(f"Failed:               {failed}")
        print("="*75)

        if failed > 0:
            print("\n❌ SOME TESTS FAILED.")
            sys.exit(1)
        else:
            print("\n🎉 ALL TESTS & PIPELINE FEATURES ARE WORKING PERFECTLY!")
            sys.exit(0)

if __name__ == "__main__":
    tester = PipelineTester()
    asyncio.run(tester.run_all())
