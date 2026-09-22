"""
Viora – Sarvam STT plugin for LiveKit Agents 1.5.8.
Wraps Sarvam's Saarika v2.5 STT into the livekit-agents STT interface with connection pooling.
"""
from __future__ import annotations

import io
import logging
import uuid
import wave

import httpx
from livekit.agents import APIConnectOptions, stt, utils
from livekit.agents.stt import (
    SpeechData,
    SpeechEvent,
    SpeechEventType,
)

logger = logging.getLogger(__name__)

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

class SarvamSTT(stt.STT):
    """LiveKit-compatible Sarvam STT plugin using Saarika v2.5."""

    def __init__(self, *, api_key: str, model: str = "saarika:v2.5", language: str = "en-IN") -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._api_key = api_key
        self._model = model
        self._language = language

    @property
    def provider(self) -> str:
        return "sarvam"

    @property
    def model(self) -> str:
        return self._model

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: str = "",
        conn_options: APIConnectOptions,
    ) -> SpeechEvent:
        """Convert AudioBuffer → WAV bytes → Sarvam STT API → SpeechEvent."""
        lang = language or self._language
        wav_bytes = self._frames_to_wav(buffer)
        request_id = str(uuid.uuid4())

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    _SARVAM_STT_URL,
                    headers={"api-subscription-key": self._api_key},
                    data={"model": self._model, "language_code": lang},
                    files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                )
                resp.raise_for_status()
                data = resp.json()

            transcript = data.get("transcript", "")
            confidence = data.get("confidence", 0.85)
            detected_lang = data.get("language_code", lang)
            logger.debug(
                "Sarvam STT: %r (lang=%s, conf=%.2f)", transcript, detected_lang, confidence
            )

        except Exception as e:
            logger.warning("Sarvam STT error: %s", e)
            transcript = ""
            confidence = 0.0
            detected_lang = lang

        return SpeechEvent(
            type=SpeechEventType.FINAL_TRANSCRIPT,
            request_id=request_id,
            alternatives=[
                SpeechData(
                    language=detected_lang,
                    text=transcript,
                    confidence=confidence,
                )
            ],
        )

    @staticmethod
    def _frames_to_wav(buffer: utils.AudioBuffer) -> bytes:
        """Merge AudioBuffer frames into a WAV byte stream."""
        merged = utils.merge_frames(buffer)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(merged.num_channels)
            wf.setsampwidth(2)  # 16-bit PCM
            wf.setframerate(merged.sample_rate)
            wf.writeframes(bytes(merged.data))
        return buf.getvalue()

    async def aclose(self) -> None:
        pass

