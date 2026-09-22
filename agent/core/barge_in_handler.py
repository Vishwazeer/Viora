"""
Viora – Barge-in and Adaptive Silence Handler.
Manages interruption detection and per-caller silence thresholds.
LiveKit Agents handles the actual audio interrupt; this module manages
the policy and state for when / how to respond to interruptions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class BargeInState:
    """Tracks barge-in events across the lifetime of a call."""
    interrupted_count: int = 0
    total_interruptions: int = 0
    last_interrupted_at: float = 0.0
    # Adaptive silence threshold in ms
    current_silence_ms: int = 800
    # Speech rate adjustments based on interruption pattern
    is_elderly_mode: bool = False


class BargeInHandler:
    """
    Manages adaptive silence thresholds and interruption recovery.

    Philosophy:
    - If a caller is being interrupted frequently → they're speaking fast/
      decisively. Reduce silence threshold to make the agent feel snappier.
    - If a caller is elderly (detected via long pauses) → increase threshold
      so we never cut them off mid-thought.
    - Every interruption resets the current TTS stream immediately.
    """

    _HOLD_PHRASES = {
        "wait", "ruko", "ek minute", "ek second", "thamba", "thoda ruko",
        "hold on", "just a second", "haan ruko",
    }

    def __init__(self, base_silence_ms: int = 800, elderly_silence_ms: int = 1200) -> None:
        self._base = base_silence_ms
        self._elderly = elderly_silence_ms
        self.state = BargeInState(current_silence_ms=base_silence_ms)

    def on_user_interrupted(self, utterance: str) -> dict:
        """
        Called when user speaks while agent is speaking.
        Returns an action dict for the pipeline to act on.
        """
        self.state.interrupted_count += 1
        self.state.total_interruptions += 1
        self.state.last_interrupted_at = time.monotonic()

        is_hold = any(p in utterance.lower() for p in self._HOLD_PHRASES)

        # Adapt silence threshold
        if self.state.interrupted_count >= 3:
            # Responsive caller – tighten up
            self.state.current_silence_ms = max(600, self._base - 100)
        elif self.state.is_elderly_mode:
            self.state.current_silence_ms = self._elderly

        return {
            "action": "hold" if is_hold else "restart_listen",
            "stop_tts": True,
            "new_silence_ms": self.state.current_silence_ms,
        }

    def on_long_pause_detected(self, pause_ms: int) -> None:
        """Called when a pause longer than 1.5s is detected mid-utterance."""
        if pause_ms > 1500:
            self.state.is_elderly_mode = True
            self.state.current_silence_ms = self._elderly

    def on_agent_finished_speaking(self) -> None:
        """Reset per-utterance interrupted count after agent finishes a full turn."""
        self.state.interrupted_count = 0

    @property
    def silence_threshold_ms(self) -> int:
        return self.state.current_silence_ms
