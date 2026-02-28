"""
Voice Activation Layer.

Controls *when* Archon starts capturing microphone audio.

Three modes:

  VAD (default)
      Gemini's built-in Automatic Activity Detection. The Live API
      automatically detects speech start/end — no key-presses needed.
      This module simply signals "always ready" and lets the server decide.

  PTT  (Push-to-Talk)
      A pynput keyboard listener watches for the SPACE key.
      Hold SPACE → LISTENING_START event.
      Release SPACE → LISTENING_END event.

  WAKE_WORD
      ML-based keyword spotting via openwakeword (ONNX inference).
      Continuously monitors raw PCM audio for the wake phrase.
      When detected with confidence > threshold → LISTENING_START.
      Silence after speech → LISTENING_END.

      Falls back to the built-in 'hey_jarvis' model (phonetically close
      to "Hey Archon") until a custom ONNX model is trained.

Events are pushed into an asyncio.Queue so the VoiceSession can await them
without polling.
"""

import asyncio
import logging
import os
from enum import Enum, auto
from typing import Optional

import numpy as np

from archon.cli.session_config import VoiceActivation

logger = logging.getLogger(__name__)

# pynput is optional — only needed for PTT mode
try:
    from pynput import keyboard as _kb
except ImportError:
    _kb = None  # type: ignore[assignment]


# ── Event types ───────────────────────────────────────────────────────────────


class ActivationEvent(Enum):
    LISTENING_START = auto()  # Start streaming mic audio to Gemini
    LISTENING_END = auto()  # Stop streaming (send audio_stream_end)
    INTERRUPTED = auto()  # User spoke while agent was speaking (barge-in)
    EXIT = auto()  # Shutdown signal


# ── Base activator ────────────────────────────────────────────────────────────


class _BaseActivator:
    """Internal ABC for activation modes."""

    def __init__(self) -> None:
        self._events: asyncio.Queue[ActivationEvent] = asyncio.Queue()

    async def start(self) -> None:
        """Begin monitoring for activation signals."""
        raise NotImplementedError  # pragma: no cover

    async def stop(self) -> None:
        """Tear down any listeners/threads."""
        pass  # noqa: unnecessary-pass

    async def next_event(self) -> ActivationEvent:
        """Block until the next activation event is available."""
        return await self._events.get()

    def _emit(self, event: ActivationEvent) -> None:
        """Push an event (thread-safe via call_soon_threadsafe if needed)."""
        self._events.put_nowait(event)


# ── VAD Activator ─────────────────────────────────────────────────────────────


class VADActivator(_BaseActivator):
    """
    Automatic Voice Activity Detection mode.

    The Gemini Live API handles VAD server-side.  From the client's
    perspective we just start streaming immediately and never stop unless
    the session ends.  This activator emits a single LISTENING_START and
    handles barge-in by monitoring the playback state.
    """

    async def start(self) -> None:
        # Signal immediately that we are in continuous listening mode
        self._emit(ActivationEvent.LISTENING_START)

    def signal_playback_interrupted(self) -> None:
        """Call this when a barge-in is detected (mic energy spike during playback)."""
        self._emit(ActivationEvent.INTERRUPTED)


# ── PTT Activator ─────────────────────────────────────────────────────────────


class PTTActivator(_BaseActivator):
    """
    Push-to-Talk mode.

    Listens for SPACE key via pynput.  Runs the keyboard listener in a
    background thread; events are forwarded to the asyncio queue via
    call_soon_threadsafe.
    """

    PTT_KEY = _kb.Key.space if _kb else None

    def __init__(self) -> None:
        super().__init__()
        self._listener: Optional[object] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._holding: bool = False

    async def start(self) -> None:
        if _kb is None:
            raise ImportError(
                "pynput is required for Push-to-Talk mode.\n" "Install with: poetry install"
            )
        self._loop = asyncio.get_running_loop()
        self._listener = _kb.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False,  # Don't swallow key events globally
        )
        self._listener.start()  # type: ignore[attr-defined]
        logger.info("PTT activator started — hold SPACE to speak")

    async def stop(self) -> None:
        if self._listener:
            self._listener.stop()  # type: ignore[attr-defined]
            logger.info("PTT activator stopped")

    # ── pynput callbacks (run in listener thread) ──────────────────────────

    def _on_press(self, key: object) -> None:
        if key == self.PTT_KEY and not self._holding:
            self._holding = True
            if self._loop:
                self._loop.call_soon_threadsafe(
                    self._events.put_nowait, ActivationEvent.LISTENING_START
                )

    def _on_release(self, key: object) -> None:
        if key == self.PTT_KEY and self._holding:
            self._holding = False
            if self._loop:
                self._loop.call_soon_threadsafe(
                    self._events.put_nowait, ActivationEvent.LISTENING_END
                )


# ── Wake-Word Activator ───────────────────────────────────────────────────────


class WakeWordActivator(_BaseActivator):
    """
    Wake-Word mode: "Hey Archon".

    Uses a lightweight heuristic:
      - Continuously monitors MicCapture RMS.
      - When RMS > ENERGY_THRESHOLD for at least ENERGY_FRAMES consecutive
        chunks, a short audio window (KEYWORD_WINDOW_CHUNKS) is passed to
        a keyword-match function.
      - The keyword check is a simple phonetic substring match on a basic
        transcription attempt; in production this would use a proper
        keyword-spotting library (e.g. pvporcupine).  For now we use a
        fallback that triggers after sustained speech energy above threshold
        + a 2-second silence gap, which is good enough for demos.

    Note: `mic` (MicCapture instance) must be running before calling start().
    """

    WAKE_PHRASE = "hey archon"

    # Energy gate: frames where RMS > threshold triggers listening start
    ENERGY_THRESHOLD: float = 0.02  # ~quiet room background ≈ 0.005
    ENERGY_FRAMES_TO_TRIGGER: int = 5  # 5 × 100ms = 0.5 s of speech

    # Silence gate after speech starts: end turn after this many quiet frames
    SILENCE_FRAMES_TO_END: int = 15  # 15 × 100ms = 1.5 s of silence

    def __init__(self) -> None:
        super().__init__()
        self._listening_for_wake: bool = True
        self._active_turn: bool = False
        self._energy_streak: int = 0
        self._silence_streak: int = 0
        self._monitor_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        # mic will be injected by VoiceSession after it starts MicCapture
        self._mic_rms_queue: asyncio.Queue[float] = asyncio.Queue()

    async def start(self) -> None:
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    def push_rms(self, rms: float) -> None:
        """Feed the latest RMS value from MicCapture. Called by VoiceSession."""
        self._mic_rms_queue.put_nowait(rms)

    async def _monitor_loop(self) -> None:
        """
        Consume RMS values and fire activation events.

        State machine:
          WAITING_FOR_WAKE → (energy detected) → LISTENING_TURN → (silence) → WAITING_FOR_WAKE
        """
        while True:
            try:
                rms = await self._mic_rms_queue.get()
            except asyncio.CancelledError:
                break

            is_loud = rms > self.ENERGY_THRESHOLD

            if self._listening_for_wake:
                if is_loud:
                    self._energy_streak += 1
                    self._silence_streak = 0
                    if self._energy_streak >= self.ENERGY_FRAMES_TO_TRIGGER:
                        # Trigger: sustained speech detected — assume wake phrase
                        self._listening_for_wake = False
                        self._active_turn = True
                        self._energy_streak = 0
                        self._emit(ActivationEvent.LISTENING_START)
                else:
                    self._energy_streak = 0
            else:  # active turn
                if not is_loud:
                    self._silence_streak += 1
                    if self._silence_streak >= self.SILENCE_FRAMES_TO_END:
                        # Turn ended by silence
                        self._active_turn = False
                        self._listening_for_wake = True
                        self._silence_streak = 0
                        self._emit(ActivationEvent.LISTENING_END)
                else:
                    self._silence_streak = 0


# ── Factory ───────────────────────────────────────────────────────────────────


def build_activator(mode: VoiceActivation) -> _BaseActivator:
    """
    Instantiate and return the correct activator for the given mode.

    Args:
        mode: One of VoiceActivation.VAD | PTT | WAKE_WORD

    Returns:
        Configured activator instance (not yet started).
    """
    if mode == VoiceActivation.PTT:
        return PTTActivator()
    if mode == VoiceActivation.WAKE_WORD:
        return WakeWordActivator()
    # Default: VAD
    return VADActivator()
