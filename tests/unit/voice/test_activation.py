"""
Tests for the voice activation layer.

Covers all three activation modes:
  - VADActivator: always-on, server-side VAD
  - PTTActivator: push-to-talk via keyboard
  - WakeWordActivator: ML-based keyword spotting via openwakeword

All tests run WITHOUT audio hardware, API keys, or real ML models.
openwakeword and pynput are mocked at the module level.
"""

import asyncio
import struct
import sys
import types
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from archon.cli.session_config import VoiceActivation
from archon.voice.activation import (
    ActivationEvent,
    PTTActivator,
    VADActivator,
    WakeWordActivator,
    _BaseActivator,
    build_activator,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_pcm_silence(duration_ms: int = 100, sample_rate: int = 16000) -> bytes:
    """Generate silent PCM bytes (all zeros)."""
    n_samples = int(sample_rate * duration_ms / 1000)
    return np.zeros(n_samples, dtype=np.int16).tobytes()


def _make_pcm_tone(
    freq: float = 440.0,
    duration_ms: int = 100,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a sine tone as PCM bytes."""
    n_samples = int(sample_rate * duration_ms / 1000)
    t = np.arange(n_samples, dtype=np.float32) / sample_rate
    signal = (amplitude * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16)
    return signal.tobytes()


# ── TestVADActivator ──────────────────────────────────────────────────────────


class TestVADActivator:
    """VAD mode: always-on, single LISTENING_START on start()."""

    @pytest.mark.asyncio
    async def test_start_emits_listening_start(self):
        activator = VADActivator()
        await activator.start()
        event = activator._events.get_nowait()
        assert event == ActivationEvent.LISTENING_START

    @pytest.mark.asyncio
    async def test_signal_playback_interrupted(self):
        activator = VADActivator()
        activator.signal_playback_interrupted()
        event = activator._events.get_nowait()
        assert event == ActivationEvent.INTERRUPTED

    @pytest.mark.asyncio
    async def test_queue_empty_after_drain(self):
        activator = VADActivator()
        await activator.start()
        _ = activator._events.get_nowait()  # drain LISTENING_START
        assert activator._events.empty()


# ── TestPTTActivator ──────────────────────────────────────────────────────────


class TestPTTActivator:
    """Push-to-Talk mode: keyboard events → activation events."""

    @pytest.mark.asyncio
    async def test_ptt_missing_pynput_raises(self):
        """If pynput is not available, start() should raise ImportError."""
        activator = PTTActivator()
        # Temporarily set _kb to None to simulate missing pynput
        with patch("archon.voice.activation._kb", None):
            with pytest.raises(ImportError, match="pynput"):
                await activator.start()

    @pytest.mark.asyncio
    async def test_ptt_press_emits_listening_start(self):
        """Simulating SPACE press should emit LISTENING_START."""
        activator = PTTActivator()
        # Simulate a key press callback directly
        activator._loop = asyncio.get_running_loop()
        activator._holding = False
        activator._on_press(activator.PTT_KEY)
        assert activator._holding is True
        # call_soon_threadsafe schedules for next iteration — yield to process it
        await asyncio.sleep(0)
        event = activator._events.get_nowait()
        assert event == ActivationEvent.LISTENING_START

    @pytest.mark.asyncio
    async def test_ptt_release_emits_listening_end(self):
        """Simulating SPACE release should emit LISTENING_END."""
        activator = PTTActivator()
        activator._loop = asyncio.get_running_loop()
        # First press
        activator._on_press(activator.PTT_KEY)
        await asyncio.sleep(0)  # process call_soon_threadsafe callback
        _ = activator._events.get_nowait()  # drain
        # Then release
        activator._on_release(activator.PTT_KEY)
        await asyncio.sleep(0)  # process call_soon_threadsafe callback
        assert activator._holding is False
        event = activator._events.get_nowait()
        assert event == ActivationEvent.LISTENING_END

    @pytest.mark.asyncio
    async def test_ptt_ignores_non_space(self):
        """Non-SPACE keys should not trigger events."""
        activator = PTTActivator()
        activator._loop = asyncio.get_running_loop()
        activator._on_press("a")
        assert activator._events.empty()
        assert activator._holding is False

    @pytest.mark.asyncio
    async def test_ptt_no_duplicate_press(self):
        """Holding SPACE should not emit multiple LISTENING_START events."""
        activator = PTTActivator()
        activator._loop = asyncio.get_running_loop()
        activator._on_press(activator.PTT_KEY)
        activator._on_press(activator.PTT_KEY)  # second press while holding
        await asyncio.sleep(0)  # process call_soon_threadsafe callbacks
        # Only one event should be in queue
        _ = activator._events.get_nowait()
        assert activator._events.empty()


# ── TestWakeWordActivator ────────────────────────────────────────────────────


class TestWakeWordActivator:
    """Wake-word mode: ML-based keyword spotting via openwakeword."""

    def _make_mock_oww(self, scores: list[float]):
        """
        Create a mock openwakeword module and model.

        Args:
            scores: List of prediction scores to return sequentially.
                    Each call to model.predict() returns the next score.
        """
        score_iter = iter(scores)

        mock_model = MagicMock()
        mock_model.predict = MagicMock(
            side_effect=lambda audio: {"hey_jarvis_v0.1": next(score_iter, 0.0)}
        )
        mock_model.reset = MagicMock()

        mock_oww_module = MagicMock()
        mock_oww_module.utils.download_models = MagicMock()

        mock_model_class = MagicMock(return_value=mock_model)

        return mock_oww_module, mock_model_class, mock_model

    @pytest.mark.asyncio
    async def test_wake_word_detection_triggers_listening_start(self):
        """When openwakeword returns score >= threshold, LISTENING_START fires."""
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww([0.0, 0.0, 0.85])

        activator = WakeWordActivator()
        activator._threshold = 0.5

        with patch.dict(sys.modules, {
            "openwakeword": mock_oww,
            "openwakeword.model": MagicMock(Model=mock_model_cls),
            "openwakeword.utils": mock_oww.utils,
        }):
            activator._oww_model = mock_model
            activator._model_key = "hey_jarvis_v0.1"
            activator._monitor_task = asyncio.create_task(activator._monitor_loop())

            # Feed 3 chunks: 2 below threshold, 1 above
            silence = _make_pcm_silence()
            activator.push_audio(silence)
            activator.push_audio(silence)
            activator.push_audio(_make_pcm_tone())

            # Wait for processing
            await asyncio.sleep(0.15)

            event = activator._events.get_nowait()
            assert event == ActivationEvent.LISTENING_START
            mock_model.reset.assert_called_once()

            activator._monitor_task.cancel()
            try:
                await activator._monitor_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_silence_after_wake_triggers_listening_end(self):
        """After wake-word triggers, sustained silence should emit LISTENING_END."""
        # First chunk triggers wake, then 15+ chunks of silence for turn end
        scores = [0.9] + [0.0] * 20
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww(scores)

        activator = WakeWordActivator()
        activator._threshold = 0.5
        activator.SILENCE_FRAMES_TO_END = 5  # reduce for faster test
        activator.ENERGY_THRESHOLD = 0.02

        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        # First chunk: wake-word detected
        activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.05)
        event = activator._events.get_nowait()
        assert event == ActivationEvent.LISTENING_START

        # Feed 6 silence chunks (> SILENCE_FRAMES_TO_END=5)
        for _ in range(6):
            activator.push_audio(_make_pcm_silence())
        await asyncio.sleep(0.15)

        event = activator._events.get_nowait()
        assert event == ActivationEvent.LISTENING_END

        activator._monitor_task.cancel()
        try:
            await activator._monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_speech_during_turn_resets_silence_streak(self):
        """Speech during an active turn should reset the silence counter."""
        scores = [0.9] + [0.0] * 20
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww(scores)

        activator = WakeWordActivator()
        activator._threshold = 0.5
        activator.SILENCE_FRAMES_TO_END = 5
        activator.ENERGY_THRESHOLD = 0.02

        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        # Trigger wake
        activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.05)
        _ = activator._events.get_nowait()  # drain LISTENING_START

        # Feed 3 silence, then 1 loud, then 3 more silence — should NOT trigger end
        for _ in range(3):
            activator.push_audio(_make_pcm_silence())
        activator.push_audio(_make_pcm_tone(amplitude=0.5))
        for _ in range(3):
            activator.push_audio(_make_pcm_silence())
        await asyncio.sleep(0.15)

        # No LISTENING_END should have fired (silence streak never reached 5)
        assert activator._events.empty()

        activator._monitor_task.cancel()
        try:
            await activator._monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_below_threshold_does_not_trigger(self):
        """Scores below threshold should not trigger wake-word."""
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww([0.1, 0.2, 0.3, 0.4])

        activator = WakeWordActivator()
        activator._threshold = 0.5
        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        for _ in range(4):
            activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.15)

        assert activator._events.empty()
        assert activator._listening_for_wake is True

        activator._monitor_task.cancel()
        try:
            await activator._monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_push_audio_accepts_bytes(self):
        """push_audio should accept raw PCM bytes without error."""
        activator = WakeWordActivator()
        pcm = _make_pcm_silence()
        activator.push_audio(pcm)
        assert not activator._audio_queue.empty()
        chunk = activator._audio_queue.get_nowait()
        assert chunk == pcm

    @pytest.mark.asyncio
    async def test_model_reset_called_on_detection(self):
        """Model should be reset after wake-word detection to prevent re-triggering."""
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww([0.9])

        activator = WakeWordActivator()
        activator._threshold = 0.5
        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.1)

        mock_model.reset.assert_called_once()

        activator._monitor_task.cancel()
        try:
            await activator._monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_load_model_missing_oww_raises(self):
        """If openwakeword is not installed, _load_model should raise ImportError."""
        activator = WakeWordActivator()

        # Hide openwakeword from imports
        with patch.dict(sys.modules, {"openwakeword": None, "openwakeword.model": None}):
            with pytest.raises(ImportError, match="openwakeword"):
                activator._load_model()

    def test_default_threshold(self):
        """Default threshold should be 0.5."""
        with patch.dict("os.environ", {}, clear=False):
            activator = WakeWordActivator()
            assert activator._threshold == 0.5

    def test_env_threshold_override(self):
        """ARCHON_WAKE_THRESHOLD env var should override default."""
        with patch.dict("os.environ", {"ARCHON_WAKE_THRESHOLD": "0.7"}):
            activator = WakeWordActivator()
            assert activator._threshold == 0.7

    def test_env_model_path(self):
        """ARCHON_WAKE_MODEL_PATH env var should be read."""
        with patch.dict("os.environ", {"ARCHON_WAKE_MODEL_PATH": "/tmp/hey_archon.onnx"}):
            activator = WakeWordActivator()
            assert activator._custom_model_path == "/tmp/hey_archon.onnx"

    @pytest.mark.asyncio
    async def test_stop_cancels_monitor_task(self):
        """stop() should cleanly cancel the monitor task."""
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww([])

        activator = WakeWordActivator()
        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        await asyncio.sleep(0.05)
        await activator.stop()
        assert activator._monitor_task.cancelled() or activator._monitor_task.done()

    @pytest.mark.asyncio
    async def test_wake_then_silence_then_wake_again(self):
        """Full cycle: wake → turn → silence → back to listening → wake again."""
        # Only predict() calls matter — silence chunks use RMS, not predict.
        # Two predict calls: first wake (0.9) and second wake (0.9).
        scores = [0.9, 0.9]
        mock_oww, mock_model_cls, mock_model = self._make_mock_oww(scores)

        activator = WakeWordActivator()
        activator._threshold = 0.5
        activator.SILENCE_FRAMES_TO_END = 3  # fast for testing
        activator.ENERGY_THRESHOLD = 0.02

        activator._oww_model = mock_model
        activator._model_key = "hey_jarvis_v0.1"
        activator._monitor_task = asyncio.create_task(activator._monitor_loop())

        # First wake
        activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.05)
        event1 = activator._events.get_nowait()
        assert event1 == ActivationEvent.LISTENING_START

        # Silence to end turn (4 chunks > SILENCE_FRAMES_TO_END=3)
        for _ in range(4):
            activator.push_audio(_make_pcm_silence())
        await asyncio.sleep(0.1)
        event2 = activator._events.get_nowait()
        assert event2 == ActivationEvent.LISTENING_END

        # Second wake
        activator.push_audio(_make_pcm_tone())
        await asyncio.sleep(0.1)
        event3 = activator._events.get_nowait()
        assert event3 == ActivationEvent.LISTENING_START

        activator._monitor_task.cancel()
        try:
            await activator._monitor_task
        except asyncio.CancelledError:
            pass


# ── TestBuildActivator ────────────────────────────────────────────────────────


class TestBuildActivator:
    """Factory function returns correct activator types."""

    def test_vad_returns_vad_activator(self):
        result = build_activator(VoiceActivation.VAD)
        assert isinstance(result, VADActivator)

    def test_ptt_returns_ptt_activator(self):
        result = build_activator(VoiceActivation.PTT)
        assert isinstance(result, PTTActivator)

    def test_wake_word_returns_wake_word_activator(self):
        result = build_activator(VoiceActivation.WAKE_WORD)
        assert isinstance(result, WakeWordActivator)


# ── TestBaseActivator ─────────────────────────────────────────────────────────


class TestBaseActivator:
    """Base activator interface tests."""

    @pytest.mark.asyncio
    async def test_emit_puts_event_in_queue(self):
        activator = VADActivator()  # concrete subclass
        activator._emit(ActivationEvent.EXIT)
        event = activator._events.get_nowait()
        assert event == ActivationEvent.EXIT

    @pytest.mark.asyncio
    async def test_next_event_blocks_until_available(self):
        activator = VADActivator()

        async def _emit_after_delay():
            await asyncio.sleep(0.05)
            activator._emit(ActivationEvent.LISTENING_START)

        asyncio.create_task(_emit_after_delay())
        event = await asyncio.wait_for(activator.next_event(), timeout=1.0)
        assert event == ActivationEvent.LISTENING_START

    @pytest.mark.asyncio
    async def test_stop_is_noop_by_default(self):
        activator = VADActivator()
        await activator.stop()  # should not raise
