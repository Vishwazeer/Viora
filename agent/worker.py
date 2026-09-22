"""
Viora – LiveKit Agent Worker
Voice pipeline: Silero VAD + Sarvam STT/TTS + Groq LLM + Appointment Tools.

Start (dev mode):
    python -m agent.worker dev
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli  # noqa: E402
from livekit.plugins import openai, silero  # noqa: E402

from agent.livekit_plugins import SarvamSTT, SarvamTTS  # noqa: E402
from agent.tools import (  # noqa: E402
    book_appointment,
    cancel_appointment,
    check_doctor_availability,
    get_clinic_info,
    list_doctors,
)
from config.settings import get_settings  # noqa: E402

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM_PROMPT = """
You are Viora, an AI-powered healthcare receptionist and voice calling agent for clinics and hospitals — handling appointment scheduling, patient intake, symptom triage, and front-desk operations.
You speak clearly and warmly in a professional medical-reception tone.
Keep every response to 1-3 short sentences — this is a voice call, not a chat.

CLINIC AT A GLANCE:
- Name: Viora Health
- Address: 42, MG Road, Koramangala, Bangalore – 560095
- Phone: +91-80-4567-8900
- OPD Hours: Monday–Saturday 9 AM–7 PM | Sunday 10 AM–2 PM
- Emergency (24x7): +91-80-4567-8999

DOCTORS (key roster):
- Dr. Priya Sharma — General Medicine (Mon, Wed, Fri)
- Dr. Rajan Mehta — Orthopedics (Tue, Thu, Sat)
- Dr. Ananya Iyer — Pediatrics (Mon–Fri)
- Dr. Suresh Nair — Cardiology (Mon, Wed, Fri)
- Dr. Kavya Reddy — Dermatology (Tue, Thu, Sat)

SERVICES: Blood tests, ECG, X-Ray, Ultrasound, Physiotherapy, Vaccination, Minor Surgery, Diabetes Clinic, Hypertension Clinic.

RULES:
1. To book an appointment, collect: patient name, phone number, preferred doctor, date and time. Then call the book_appointment tool.
2. Always confirm back the details before booking.
3. If a patient reports chest pain, breathing difficulty, or stroke symptoms — immediately say "Please call 112 or go to the nearest emergency room right now."
4. If they ask for a human, say "I'll transfer you to our front desk. Please hold."
5. Speak naturally — avoid listing bullet points out loud.
6. If asked about doctors not in our clinic, politely say we don't have that specialist and suggest the closest match.
""".strip()


class VioraAgent(Agent):
    """Viora — AI voice receptionist"""

    def __init__(self) -> None:
        super().__init__(
            instructions=_SYSTEM_PROMPT,
            tools=[
                get_clinic_info,
                list_doctors,
                check_doctor_availability,
                book_appointment,
                cancel_appointment,
            ],
        )

    async def on_enter(self) -> None:
        """Greet the caller as soon as the agent joins."""
        await self.session.say(
            "Namaste! Thank you for calling. "
            "I'm Viora, your AI receptionist. "
            "How may I help you today?",
            allow_interruptions=True,
        )


async def entrypoint(ctx: JobContext) -> None:
    """One LiveKit job = one call session."""
    logger.info("New call session — room: %s", ctx.room.name)
    started_at = datetime.now(UTC)

    session = AgentSession(
        vad=silero.VAD.load(min_speech_duration=0.05, min_silence_duration=0.5),
        stt=SarvamSTT(
            api_key=settings.SARVAM_API_KEY,
            model=settings.SARVAM_STT_MODEL,
            language=settings.DEFAULT_LANGUAGE,
        ),
        llm=openai.LLM(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model=settings.GROQ_MODEL,
        ),
        tts=SarvamTTS(
            api_key=settings.SARVAM_API_KEY,
            model=settings.SARVAM_TTS_MODEL,
            voice=settings.SARVAM_DEFAULT_VOICE,
            language=settings.DEFAULT_LANGUAGE,
            speed=settings.SARVAM_TTS_SPEED,
        ),
    )


    await session.start(VioraAgent(), room=ctx.room)
    logger.info("Viora session started — room: %s", ctx.room.name)

    disconnect_fut: asyncio.Future[None] = asyncio.get_event_loop().create_future()

    @ctx.room.on("disconnected")
    def _on_disconnect(*_args: object) -> None:
        if not disconnect_fut.done():
            disconnect_fut.set_result(None)

    await disconnect_fut
    logger.info("Room disconnected — saving call log for %s", ctx.room.name)

    # Persist call log (best-effort)
    try:
        from db.models import CallIntent, CallLog, CallOutcome
        from db.session import get_db_context

        ended_at = datetime.now(UTC)
        duration = int((ended_at - started_at).total_seconds())

        transcript: list[dict] = []
        if hasattr(session, "history") and session.history is not None:
            for msg in session.history.messages():
                text = getattr(msg, "text_content", None)
                if text:
                    transcript.append({"role": str(msg.role), "text": text})

        async with get_db_context() as db:
            log = CallLog(
                livekit_room_name=ctx.room.name,
                patient_phone="browser-simulator",
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=duration,
                turn_count=len(transcript),
                transcript=transcript,
                outcome=CallOutcome.RESOLVED if len(transcript) > 2 else CallOutcome.ABANDONED,
                primary_intent=CallIntent.UNKNOWN,
            )
            db.add(log)
        logger.info("Call log saved for %s", ctx.room.name)
    except Exception as exc:
        logger.warning("Could not save call log (non-fatal): %s", exc)


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
