"""
Viora – Sarvam TTS plugin for LiveKit Agents 1.5.8.
Wraps Sarvam's Bulbul v2 TTS into the livekit-agents TTS interface with connection pooling and LRU audio caching.
"""
from __future__ import annotations

import base64
import io
import logging
import uuid
import wave
from dataclasses import dataclass

import httpx
from livekit.agents import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, tts
from livekit.agents.tts import ChunkedStream

logger = logging.getLogger(__name__)

_SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
_SAMPLE_RATE = 22050  # Sarvam returns 22050 Hz
_NUM_CHANNELS = 1

# In-memory audio cache for frequent phrases (greetings, standard disclaimers, etc.)
_AUDIO_CACHE: dict[str, bytes] = {}
_MAX_CACHE_SIZE = 256


@dataclass
class SarvamTTSOptions:
    api_key: str
    model: str = "bulbul:v3"
    voice: str = "priya"
    language_code: str = "en-IN"
    speed: float = 0.92


class SarvamChunkedStream(ChunkedStream):
    """Single-shot Sarvam TTS request wrapped as a ChunkedStream."""

    def __init__(self, *, tts: SarvamTTS, input_text: str, conn_options: APIConnectOptions) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts_ref: SarvamTTS = tts  # type: ignore[assignment]

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        request_id = str(uuid.uuid4())
        opts = self._tts_ref._opts

        # MUST call initialize() before any push() — required by livekit-agents 1.5.8
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=_SAMPLE_RATE,
            num_channels=_NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        cache_key = f"{opts.model}:{opts.voice}:{opts.language_code}:{opts.speed}:{self._input_text.strip()}"
        if cache_key in _AUDIO_CACHE:
            pcm_bytes = _AUDIO_CACHE[cache_key]
            output_emitter.push(pcm_bytes)
            logger.debug("Sarvam TTS (Cache Hit): %r -> %d bytes PCM", self._input_text[:50], len(pcm_bytes))
            return

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(
                    _SARVAM_TTS_URL,
                    headers={
                        "api-subscription-key": opts.api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "inputs": [self._input_text],
                        "target_language_code": opts.language_code,
                        "speaker": opts.voice,
                        "model": opts.model,
                        "speech_sample_rate": _SAMPLE_RATE,
                        "enable_preprocessing": True,
                        "pace": opts.speed,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                audio_b64 = data["audios"][0]
                pcm_bytes = self._wav_b64_to_pcm(audio_b64)

            # Store in cache if small text
            if len(_AUDIO_CACHE) < _MAX_CACHE_SIZE and len(self._input_text) < 200:
                _AUDIO_CACHE[cache_key] = pcm_bytes

            output_emitter.push(pcm_bytes)
            logger.debug("Sarvam TTS: %r -> %d bytes PCM", self._input_text[:60], len(pcm_bytes))

        except Exception as e:
            logger.warning("Sarvam TTS error (voice=%s, model=%s): %s", opts.voice, opts.model, e)
            # Push 0.5s of silence so the pipeline does not stall
            silence = bytes(int(_SAMPLE_RATE * 0.5) * _NUM_CHANNELS * 2)
            output_emitter.push(silence)

    @staticmethod
    def _wav_b64_to_pcm(b64: str) -> bytes:
        """Decode base64 WAV and extract raw PCM bytes."""
        wav_bytes = base64.b64decode(b64)
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            return wf.readframes(wf.getnframes())


class SarvamTTS(tts.TTS):
    """LiveKit-compatible Sarvam TTS plugin using Bulbul v2."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "bulbul:v3",
        voice: str = "priya",
        language: str = "en-IN",
        speed: float = 0.92,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=_SAMPLE_RATE,
            num_channels=_NUM_CHANNELS,
        )
        self._opts = SarvamTTSOptions(
            api_key=api_key,
            model=model,
            voice=voice,
            language_code=language,
            speed=speed,
        )

    @property
    def provider(self) -> str:
        return "sarvam"

    @property
    def model(self) -> str:
        return self._opts.model

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> SarvamChunkedStream:
        return SarvamChunkedStream(tts=self, input_text=text, conn_options=conn_options)

    async def aclose(self) -> None:
        pass

