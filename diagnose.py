import asyncio
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent / ".env")

# Must set path so we can import project modules
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings  # noqa: E402


class DiagnosticRunner:
    def __init__(self):
        self.settings = get_settings()
        self.results = []
        self.has_failures = False

    def report(self, name: str, status: bool, details: str = ""):
        icon = "[PASS]" if status else "[FAIL]"
        if not status:
            self.has_failures = True
        self.results.append(f"{icon} | {name.ljust(25)} | {details}")
        print(self.results[-1])

    async def check_env_vars(self):
        print("\n--- Checking Environment Variables ---")
        required = [
            'LIVEKIT_URL', 'LIVEKIT_API_KEY', 'LIVEKIT_API_SECRET',
            'SARVAM_API_KEY', 'GROQ_API_KEY'
        ]
        all_ok = True
        for key in required:
            val = getattr(self.settings, key, None)
            if val:
                masked = f"{val[:8]}..." if len(val) > 8 else "***"
                self.report(key, True, masked)
            else:
                self.report(key, False, "Missing or Empty")
                all_ok = False
        return all_ok

    async def check_sarvam_tts(self):
        print("\n--- Checking Sarvam TTS ---")
        try:
            from agent.livekit_plugins import SarvamTTS
            tts = SarvamTTS(api_key=self.settings.SARVAM_API_KEY, voice=self.settings.SARVAM_DEFAULT_VOICE)
            stream = tts.synthesize("This is a diagnostic test.")
            frames = []
            async for audio in stream:
                frames.append(audio.frame)
            duration = sum(f.duration for f in frames)
            self.report("Sarvam TTS API", True, f"Synthesized {len(frames)} frames ({duration:.2f}s)")
            return True
        except Exception as e:
            self.report("Sarvam TTS API", False, str(e))
            return False

    async def check_sarvam_stt(self):
        print("\n--- Checking Sarvam STT ---")
        try:
            from livekit import rtc
            from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

            from agent.livekit_plugins import SarvamSTT
            stt = SarvamSTT(api_key=self.settings.SARVAM_API_KEY, model=self.settings.SARVAM_STT_MODEL)
            # Send 1 second of silence
            silence = rtc.AudioFrame(data=bytes(16000*2), sample_rate=16000, num_channels=1, samples_per_channel=16000)
            result = await stt.recognize([silence], conn_options=DEFAULT_API_CONNECT_OPTIONS)
            self.report("Sarvam STT API", True, f"Responded with type: {result.type}")
            return True
        except Exception as e:
            self.report("Sarvam STT API", False, str(e))
            return False

    async def check_groq_llm(self):
        print("\n--- Checking Groq LLM ---")
        try:
            from livekit.agents.llm import ChatContext
            from livekit.plugins import openai
            llm = openai.LLM(
                api_key=self.settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1",
                model=self.settings.GROQ_MODEL
            )
            ctx = ChatContext()
            ctx.add_message(role='user', content='Say "OK" and nothing else.')
            stream = llm.chat(chat_ctx=ctx)
            text = ""
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    text += chunk.delta.content
            self.report("Groq LLM API", True, f"Response: {text.strip()}")
            return True
        except Exception as e:
            self.report("Groq LLM API", False, str(e))
            return False

    async def check_livekit_connection(self):
        print("\n--- Checking LiveKit Connection ---")
        try:
            from livekit.api import ListRoomsRequest, LiveKitAPI
            api = LiveKitAPI(
                self.settings.LIVEKIT_URL,
                self.settings.LIVEKIT_API_KEY,
                self.settings.LIVEKIT_API_SECRET
            )
            # Try to list rooms
            rooms = await api.room.list_rooms(ListRoomsRequest())
            self.report("LiveKit API", True, f"Connected. Active rooms: {len(rooms.rooms)}")
            await api.aclose()
            return True
        except Exception as e:
            self.report("LiveKit API", False, str(e))
            return False

    async def run_all(self):
        print(f"Starting Viora Diagnostics at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        env_ok = await self.check_env_vars()
        if not env_ok:
            print("\n⚠️ Environment variables missing. Skipping external API checks.")
        else:
            await self.check_livekit_connection()
            await self.check_sarvam_tts()
            await self.check_sarvam_stt()
            await self.check_groq_llm()

        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)
        for res in self.results:
            print(res)
        print("="*60)

        if self.has_failures:
            print("\n[FAIL] SOME CHECKS FAILED. See details above.")
            sys.exit(1)
        else:
            print("\n[PASS] ALL SYSTEMS GO! The agent pipeline is healthy.")
            sys.exit(0)

if __name__ == "__main__":
    runner = DiagnosticRunner()
    asyncio.run(runner.run_all())
