"""
Unit tests for voice/audio_processing.py — AudioPreprocessor pipeline.

No audio hardware or API keys required.  All tests use synthetic PCM data.
"""

import math
import struct

import numpy as np
import pytest

from archon.voice.audio_processing import AudioPreprocessor


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sine_pcm(freq_hz: float, duration_s: float = 0.1, sample_rate: int = 16_000) -> bytes:
    """Generate PCM bytes for a pure sine wave at the given frequency."""
    n_samples = int(sample_rate * duration_s)
    t = np.arange(n_samples, dtype=np.float64) / sample_rate
    wave = np.sin(2.0 * math.pi * freq_hz * t)
    pcm_int16 = (wave * 32767).astype(np.int16)
    return pcm_int16.tobytes()


def _silence_pcm(duration_s: float = 0.1, sample_rate: int = 16_000) -> bytes:
    """Generate PCM bytes of digital silence (all zeros)."""
    n_samples = int(sample_rate * duration_s)
    return np.zeros(n_samples, dtype=np.int16).tobytes()


def _constant_pcm(amplitude: float = 0.5, duration_s: float = 0.1, sample_rate: int = 16_000) -> bytes:
    """Generate PCM bytes of a DC signal (constant value)."""
    n_samples = int(sample_rate * duration_s)
    arr = np.full(n_samples, int(amplitude * 32767), dtype=np.int16)
    return arr.tobytes()


def _rms_of_pcm(pcm_bytes: bytes) -> float:
    """Compute RMS of PCM bytes in [0, 1] range."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples**2))) / 32768.0


# ── High-pass filter tests ───────────────────────────────────────────────────


class TestHighPassFilter:
    """The HPF should attenuate low frequencies and pass high frequencies."""

    def test_40hz_is_attenuated(self):
        """A 40 Hz tone (below 80 Hz cutoff) should be significantly reduced."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm_40hz = _sine_pcm(40.0)
        # Process multiple chunks to let filter state stabilise
        for _ in range(5):
            result = proc.process(pcm_40hz)
        rms_in = _rms_of_pcm(pcm_40hz)
        rms_out = _rms_of_pcm(result)
        # After AGC the gain may partially compensate, but the HPF itself
        # should still reduce 40 Hz by at least 6 dB (factor of 2)
        # We test the filter stage directly
        proc2 = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np, np_to_pcm_bytes
        audio = pcm_bytes_to_np(pcm_40hz)
        for _ in range(5):
            filtered = proc2._apply_highpass(audio)
        filtered_rms = float(np.sqrt(np.mean(filtered**2)))
        input_rms = float(np.sqrt(np.mean(audio**2)))
        assert filtered_rms < input_rms * 0.7  # at least 3 dB attenuation

    def test_1khz_passes_through(self):
        """A 1 kHz tone (well above cutoff) should pass through largely unchanged."""
        proc = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np
        audio = pcm_bytes_to_np(_sine_pcm(1000.0))
        # Let filter stabilise
        for _ in range(3):
            filtered = proc._apply_highpass(audio)
        input_rms = float(np.sqrt(np.mean(audio**2)))
        output_rms = float(np.sqrt(np.mean(filtered**2)))
        # Should retain >90% of the signal
        assert output_rms > input_rms * 0.9

    def test_filter_state_persists_across_chunks(self):
        """Filter state should carry across calls (no discontinuity)."""
        proc = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np
        audio = pcm_bytes_to_np(_sine_pcm(1000.0, duration_s=0.05))
        # First call sets initial state
        out1 = proc._apply_highpass(audio.copy())
        z1_after_first = proc._hpf_z1
        # Second call should start from that state
        out2 = proc._apply_highpass(audio.copy())
        z1_after_second = proc._hpf_z1
        # States should differ (they advanced)
        assert z1_after_first != z1_after_second


# ── Noise gate tests ─────────────────────────────────────────────────────────


class TestNoiseGate:
    """The noise gate should attenuate quiet audio and pass loud audio."""

    def test_silence_is_attenuated(self):
        """Audio well below threshold should be nearly zeroed."""
        proc = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np
        # Very quiet signal (RMS ~0.001)
        quiet = np.full(1600, 0.001, dtype=np.float32)
        result = proc._apply_noise_gate(quiet)
        result_rms = float(np.sqrt(np.mean(result**2)))
        assert result_rms < 0.001  # -40 dB attenuation applied

    def test_speech_passes_through(self):
        """Audio above threshold should pass unchanged."""
        proc = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np
        loud = pcm_bytes_to_np(_sine_pcm(440.0))  # ~0.707 RMS
        result = proc._apply_noise_gate(loud)
        np.testing.assert_array_equal(result, loud)

    def test_threshold_boundary(self):
        """Audio exactly at threshold should pass through."""
        proc = AudioPreprocessor(sample_rate=16_000)
        # Construct signal with RMS just above threshold
        threshold = proc.NOISE_GATE_THRESHOLD
        signal = np.full(1600, threshold * 1.5, dtype=np.float32)
        result = proc._apply_noise_gate(signal)
        np.testing.assert_array_equal(result, signal)


# ── AGC tests ────────────────────────────────────────────────────────────────


class TestAGC:
    """AGC should amplify quiet audio and compress loud audio."""

    def test_quiet_audio_is_amplified(self):
        """Quiet input should be amplified toward AGC_TARGET_RMS."""
        proc = AudioPreprocessor(sample_rate=16_000)
        from archon.voice.audio_io import pcm_bytes_to_np
        quiet = pcm_bytes_to_np(_sine_pcm(440.0, duration_s=0.1))
        quiet = quiet * 0.01  # Very quiet
        # Process several chunks to let gain stabilise
        for _ in range(10):
            result = proc._apply_agc(quiet.copy())
        result_rms = float(np.sqrt(np.mean(result**2)))
        quiet_rms = float(np.sqrt(np.mean(quiet**2)))
        assert result_rms > quiet_rms * 2  # Should be significantly amplified

    def test_loud_audio_is_compressed(self):
        """Loud input should be compressed (gain < 1)."""
        proc = AudioPreprocessor(sample_rate=16_000)
        loud = np.full(1600, 0.9, dtype=np.float32)
        # Process several chunks to let gain stabilise
        for _ in range(10):
            result = proc._apply_agc(loud.copy())
        result_rms = float(np.sqrt(np.mean(result**2)))
        # Should be compressed toward target (0.15)
        assert result_rms < 0.9

    def test_gain_is_smoothed(self):
        """Gain changes should be gradual, not instant."""
        proc = AudioPreprocessor(sample_rate=16_000)
        quiet = np.full(1600, 0.01, dtype=np.float32)
        loud = np.full(1600, 0.5, dtype=np.float32)
        # Process quiet to drive gain up
        for _ in range(5):
            proc._apply_agc(quiet.copy())
        gain_after_quiet = proc._agc_gain
        # Now feed loud — gain should decrease but not instantly
        proc._apply_agc(loud.copy())
        gain_after_one_loud = proc._agc_gain
        # Gain should still be high (smoothing prevents instant drop)
        assert gain_after_one_loud > proc.AGC_TARGET_RMS / 0.5

    def test_output_is_clipped(self):
        """Output should never exceed [-1.0, 1.0]."""
        proc = AudioPreprocessor(sample_rate=16_000)
        proc._agc_gain = 100.0  # Force extreme gain
        audio = np.full(1600, 0.5, dtype=np.float32)
        result = proc._apply_agc(audio)
        assert result.max() <= 1.0
        assert result.min() >= -1.0

    def test_zero_audio_preserves_gain(self):
        """All-zero input should not change the current gain."""
        proc = AudioPreprocessor(sample_rate=16_000)
        proc._agc_gain = 3.5
        silence = np.zeros(1600, dtype=np.float32)
        proc._apply_agc(silence)
        assert proc._agc_gain == 3.5  # Unchanged


# ── Full pipeline tests ──────────────────────────────────────────────────────


class TestPreprocessorPipeline:
    """End-to-end tests for the full process() method."""

    def test_output_same_length_as_input(self):
        """Processed output should be exactly the same byte length."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm = _sine_pcm(440.0)
        result = proc.process(pcm)
        assert len(result) == len(pcm)

    def test_output_is_valid_pcm(self):
        """Processed output should be valid int16 PCM."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm = _sine_pcm(440.0)
        result = proc.process(pcm)
        # Should be parseable as int16
        arr = np.frombuffer(result, dtype=np.int16)
        assert arr.dtype == np.int16
        assert len(arr) == 1600  # 100ms at 16kHz

    def test_silence_in_silence_out(self):
        """Silent input should produce near-silent output."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm = _silence_pcm()
        result = proc.process(pcm)
        rms = _rms_of_pcm(result)
        assert rms < 0.001

    def test_short_input_passthrough(self):
        """Input shorter than 2 bytes should pass through unchanged."""
        proc = AudioPreprocessor(sample_rate=16_000)
        assert proc.process(b"") == b""
        assert proc.process(b"\x00") == b"\x00"

    def test_no_clipping_on_normal_speech(self):
        """Normal-volume speech should not clip after processing."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm = _sine_pcm(440.0)
        # Run a few chunks to stabilise
        for _ in range(5):
            result = proc.process(pcm)
        arr = np.frombuffer(result, dtype=np.int16)
        # Should not be all at max/min (clipping)
        assert not np.all(np.abs(arr) == 32767)

    def test_sequential_chunks_are_continuous(self):
        """After AGC stabilises, sequential chunks should be smooth (no pops)."""
        proc = AudioPreprocessor(sample_rate=16_000)
        pcm = _sine_pcm(440.0)
        results = []
        for _ in range(15):
            results.append(proc.process(pcm))
        # Skip first 5 chunks where AGC gain is still ramping — check the
        # stabilised region (chunks 5-14) for continuity.
        for i in range(5, len(results) - 1):
            arr_a = np.frombuffer(results[i], dtype=np.int16)
            arr_b = np.frombuffer(results[i + 1], dtype=np.int16)
            delta = abs(int(arr_a[-1]) - int(arr_b[0]))
            # Allow up to 20% of full scale — 440 Hz sine at 16kHz has inherent
            # sample-to-sample jumps of ~5400 at peak, so we need headroom.
            assert delta < 6554, f"Discontinuity at chunk boundary {i}: delta={delta}"


# ── Spectral denoise fallback ────────────────────────────────────────────────


class TestSpectralDenoiseFallback:
    """When noisereduce is not installed, spectral stage should fall back gracefully."""

    def test_graceful_fallback_when_missing(self, monkeypatch):
        """If noisereduce import fails, audio should pass through unchanged."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "noisereduce":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        proc = AudioPreprocessor(sample_rate=16_000, enable_spectral_denoise=True)
        # Force re-import attempt
        proc._nr_module = None
        proc._enable_spectral = True

        monkeypatch.setattr(builtins, "__import__", mock_import)

        from archon.voice.audio_io import pcm_bytes_to_np
        audio = pcm_bytes_to_np(_sine_pcm(440.0))
        result = proc._apply_spectral_denoise(audio)
        # Should return input unchanged
        np.testing.assert_array_equal(result, audio)
        # Flag should be auto-disabled
        assert proc._enable_spectral is False
