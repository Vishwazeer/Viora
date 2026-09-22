"""
Viora – Gemini LLM plugin for LiveKit Agents 1.5.8.
Uses the google-genai SDK for Gemini 2.x models.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from google import genai
from google.genai import types as genai_types
from livekit.agents import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, llm
from livekit.agents.llm import (
    ChatChunk,
    ChatContext,
    ChoiceDelta,
    LLMStream,
)

logger = logging.getLogger(__name__)


class GeminiLLMStream(LLMStream):
    """Generates a Gemini response and emits it as a single ChatChunk."""

    async def _run(self) -> None:
        request_id = str(uuid.uuid4())

        # Build conversation history from ChatContext
        contents: list[genai_types.Content] = []
        for msg in self._chat_ctx.messages():
            text = msg.text_content or ""
            if not text:
                continue
            role = "user" if msg.role == "user" else "model"
            contents.append(
                genai_types.Content(role=role, parts=[genai_types.Part(text=text)])
            )

        if not contents:
            # Nothing to process — emit an empty chunk and exit
            self._event_ch.send_nowait(
                ChatChunk(id=request_id, delta=ChoiceDelta(role="assistant", content=""))
            )
            return

        try:
            client: genai.Client = self._llm._client  # type: ignore[attr-defined]
            model_name: str = self._llm._model_name  # type: ignore[attr-defined]
            config: genai_types.GenerateContentConfig = self._llm._config  # type: ignore[attr-defined]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                ),
            )
            text = response.text or ""
            logger.debug("Gemini response: %r", text[:80])
        except Exception as e:
            logger.warning("Gemini error: %s", e)
            text = "I'm sorry, I'm having a moment. Could you repeat that?"

        self._event_ch.send_nowait(
            ChatChunk(
                id=request_id,
                delta=ChoiceDelta(role="assistant", content=text),
            )
        )


class GeminiLLM(llm.LLM):
    """LiveKit-compatible Gemini LLM plugin using google-genai SDK."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.3,
        max_tokens: int = 512,
        system_prompt: str = "",
    ) -> None:
        super().__init__()
        self._client = genai.Client(api_key=api_key)
        self._model_name = model
        self._config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt or None,
        )

    @property
    def provider(self) -> str:
        return "google"

    @property
    def model(self) -> str:
        return self._model_name

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list[llm.Tool] | None = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
        **kwargs,
    ) -> GeminiLLMStream:
        return GeminiLLMStream(
            llm=self,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )

    async def aclose(self) -> None:
        pass
