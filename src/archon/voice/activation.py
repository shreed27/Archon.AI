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

# Default built-in model (phonetically close to "Hey Archon")
_FALLBACK_MODEL = "hey_jarvis_v0.1"


class WakeWordActivator(_BaseActivator):
    """
    Wake-Word mode: "Hey Archon".

    Uses openwakeword for ML-based keyword spotting with ONNX inference.
    Continuously monitors raw PCM audio from MicCapture and fires
    activation events when the wake phrase is detected.

    Falls back to the built-in 'hey_jarvis' model (phonetically close
    to "Hey Archon") until a custom ONNX model is trained and configured
    via ARCHON_WAKE_MODEL_PATH.

    State machine::

      WAITING_FOR_WAKE → openwakeword score > threshold → emit LISTENING_START
                                         ↓
      ACTIVE_TURN → silence (15 frames = 1.5s) → emit LISTENING_END
                                         ↓
                                WAITING_FOR_WAKE

    Custom "Hey Archon" Model Training:
      1. Generate synthetic "Hey Archon" utterances via Google Cloud TTS
         (multiple voices, speeds, accents — at least 200 positive samples).
      2. Collect ~2000 negative samples (random speech, noise, music).
      3. Run openwakeword training pipeline:
         ``openwakeword.train_custom_model(positive_dir, negative_dir, output_path)``
      4. Export .onnx model, set ARCHON_WAKE_MODEL_PATH=/path/to/hey_archon.onnx

    Environment variables:
      ARCHON_WAKE_MODEL_PATH  — path to custom ONNX wake-word model
      ARCHON_WAKE_THRESHOLD   — detection confidence threshold [0-1] (default 0.5)
    """

    # Silence gate: end turn after this many consecutive quiet frames
    SILENCE_FRAMES_TO_END: int = 15  # 15 × 100ms = 1.5 s of silence
    ENERGY_THRESHOLD: float = 0.02  # RMS threshold for silence detection during active turn

    def __init__(self) -> None:
        super().__init__()
        self._listening_for_wake: bool = True
        self._active_turn: bool = False
        self._silence_streak: int = 0
        self._monitor_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

        # Audio queue — receives raw PCM bytes from VoiceSession
        self._audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

        # openwakeword model (loaded in start())
        self._oww_model: Optional[object] = None
        self._model_key: Optional[str] = None

        # Configuration from environment
        self._custom_model_path: Optional[str] = os.getenv("ARCHON_WAKE_MODEL_PATH")
        self._threshold: float = float(os.getenv("ARCHON_WAKE_THRESHOLD", "0.5"))

    async def start(self) -> None:
        """Initialize openwakeword model and start the monitoring loop."""
        self._oww_model, self._model_key = self._load_model()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Wake-word activator started — say the wake phrase to begin")

    async def stop(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Wake-word activator stopped")

    def push_audio(self, pcm_bytes: bytes) -> None:
        """
        Feed raw PCM audio from MicCapture.

        Called by VoiceSession on every mic chunk. The audio is queued
        and consumed by the background monitor task for wake-word detection.

        Args:
            pcm_bytes: Raw LINEAR16 mono PCM at 16 kHz (int16 bytes).
        """
        self._audio_queue.put_nowait(pcm_bytes)

    # ── Model loading ─────────────────────────────────────────────────────

    def _load_model(self) -> tuple:
        """
        Lazy-load openwakeword and initialise the detection model.

        Returns:
            (model, model_key) tuple where model_key is the name used to
            look up prediction scores from the model's output dict.

        Raises:
            ImportError: If openwakeword is not installed.
        """
        try:
            import openwakeword
            from openwakeword.model import Model as OWWModel
        except ImportError:
            raise ImportError(
                "openwakeword is required for Wake-Word mode.\n"
                "Install with: pip install openwakeword"
            )

        # Download built-in models if not already cached
        openwakeword.utils.download_models()

        if self._custom_model_path:
            model = OWWModel(wakeword_models=[self._custom_model_path])
            from pathlib import Path

            model_key = Path(self._custom_model_path).stem
            logger.info("Loaded custom wake-word model: %s (threshold=%.2f)", model_key, self._threshold)
        else:
            model = OWWModel(wakeword_models=[_FALLBACK_MODEL])
            model_key = _FALLBACK_MODEL
            logger.info(
                "Using fallback wake-word model '%s' (threshold=%.2f). "
                "Set ARCHON_WAKE_MODEL_PATH for a custom 'Hey Archon' model.",
                _FALLBACK_MODEL,
                self._threshold,
            )

        return model, model_key

    # ── Monitor loop ──────────────────────────────────────────────────────

    async def _monitor_loop(self) -> None:
        """
        Consume raw PCM audio and fire activation events.

        In WAITING_FOR_WAKE state: runs openwakeword inference on each chunk.
        In ACTIVE_TURN state: monitors RMS for silence to end the turn.
        """
        while True:
            try:
                pcm_bytes = await self._audio_queue.get()
            except asyncio.CancelledError:
                break

            # Convert PCM bytes to int16 numpy array (openwakeword native format)
            audio_i16 = np.frombuffer(pcm_bytes, dtype=np.int16)

            if self._listening_for_wake:
                # ── Wake-word detection ──────────────────────────────────
                prediction = self._oww_model.predict(audio_i16)  # type: ignore[union-attr]
                score = prediction.get(self._model_key, 0.0)

                if score >= self._threshold:
                    logger.info(
                        "Wake-word detected! (model=%s, score=%.3f, threshold=%.3f)",
                        self._model_key,
                        score,
                        self._threshold,
                    )
                    self._listening_for_wake = False
                    self._active_turn = True
                    self._silence_streak = 0
                    # Reset model state so it doesn't re-trigger on residual audio
                    self._oww_model.reset()  # type: ignore[union-attr]
                    self._emit(ActivationEvent.LISTENING_START)

            else:
                # ── Active turn: monitor for silence ─────────────────────
                audio_f32 = audio_i16.astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(audio_f32**2)))

                if rms < self.ENERGY_THRESHOLD:
                    self._silence_streak += 1
                    if self._silence_streak >= self.SILENCE_FRAMES_TO_END:
                        logger.debug(
                            "Wake-word turn ended by silence (%d frames)",
                            self._silence_streak,
                        )
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
