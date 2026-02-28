"""
Audio Preprocessing Pipeline.

Applied to raw microphone PCM *before* sending to the Gemini Live API.
Cleans the signal so the server-side ASR receives higher-quality audio,
improving recognition accuracy across accents and noisy environments.

Pipeline stages (applied in order):
  1. High-pass filter  — 2nd-order Butterworth biquad, 80 Hz cutoff.
                          Removes HVAC hum, AC rumble, low-freq mechanical noise.
  2. Noise gate        — RMS-threshold gate with soft attenuation (-40 dB).
                          Suppresses background hiss during pauses.
  3. AGC               — Automatic Gain Control with EMA-smoothed gain.
                          Normalises volume across mic distances.
  4. Spectral denoise  — (optional) noisereduce spectral gating.
                          Heavy-duty cleanup for cafés / open offices.
                          Enabled via ARCHON_NOISE_REDUCE=1.

All stages are stateful — filter memory and gain state carry across chunk
boundaries so audio is continuous with no clicks or pops at seams.

Usage::

    preprocessor = AudioPreprocessor()
    for chunk in mic:
        clean = preprocessor.process(chunk)
        await sess.send_audio(clean)
"""

import logging
import math
import os
from typing import Optional, Tuple

import numpy as np

from archon.voice.audio_io import pcm_bytes_to_np, np_to_pcm_bytes

logger = logging.getLogger(__name__)

# ── Configuration (overridable via env vars) ──────────────────────────────────

_HPF_CUTOFF_HZ = float(os.getenv("ARCHON_HPF_CUTOFF", "80"))
_NOISE_GATE_THRESHOLD = float(os.getenv("ARCHON_NOISE_GATE_THRESHOLD", "0.008"))
_AGC_TARGET_RMS = float(os.getenv("ARCHON_AGC_TARGET", "0.15"))


class AudioPreprocessor:
    """
    Stateful audio preprocessor.  One instance per VoiceSession.

    Maintains biquad filter state and AGC gain across chunk boundaries
    so the processed output is a seamless, continuous stream.
    """

    # High-pass filter
    HPF_CUTOFF_HZ: float = _HPF_CUTOFF_HZ

    # Noise gate
    NOISE_GATE_THRESHOLD: float = _NOISE_GATE_THRESHOLD
    NOISE_GATE_ATTENUATION: float = 0.01  # -40 dB (soft, not hard zero)

    # Automatic Gain Control
    AGC_TARGET_RMS: float = _AGC_TARGET_RMS
    AGC_MAX_GAIN: float = 10.0
    AGC_SMOOTHING: float = 0.95  # EMA coefficient (higher = smoother)

    def __init__(
        self,
        sample_rate: int = 16_000,
        enable_spectral_denoise: bool = False,
    ) -> None:
        self.sample_rate = sample_rate
        self._enable_spectral = enable_spectral_denoise

        # Biquad high-pass filter state (Direct Form II transposed)
        self._hpf_coeffs = self._compute_hpf_coeffs()
        self._hpf_z1: float = 0.0
        self._hpf_z2: float = 0.0

        # AGC state
        self._agc_gain: float = 1.0

        # Spectral denoise (lazy-loaded)
        self._nr_module: Optional[object] = None

        logger.info(
            "AudioPreprocessor initialised: hpf=%dHz gate=%.4f agc_target=%.2f spectral=%s",
            int(self.HPF_CUTOFF_HZ),
            self.NOISE_GATE_THRESHOLD,
            self.AGC_TARGET_RMS,
            self._enable_spectral,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, pcm_bytes: bytes) -> bytes:
        """
        Apply the full preprocessing pipeline to a PCM chunk.

        Args:
            pcm_bytes: Raw LINEAR16 mono PCM at ``self.sample_rate``.

        Returns:
            Processed PCM bytes — same format and length as input.
        """
        if len(pcm_bytes) < 2:
            return pcm_bytes

        audio = pcm_bytes_to_np(pcm_bytes)

        audio = self._apply_highpass(audio)
        audio = self._apply_noise_gate(audio)
        audio = self._apply_agc(audio)

        if self._enable_spectral:
            audio = self._apply_spectral_denoise(audio)

        return np_to_pcm_bytes(audio)

    # ── Stage 1: High-pass filter ─────────────────────────────────────────────

    def _compute_hpf_coeffs(self) -> Tuple[float, float, float, float, float]:
        """
        Compute biquad coefficients for a 2nd-order Butterworth high-pass.

        Uses the bilinear transform of the analog Butterworth prototype.
        Returns (b0, b1, b2, a1, a2) normalised by a0.
        """
        w0 = 2.0 * math.pi * self.HPF_CUTOFF_HZ / self.sample_rate
        cos_w0 = math.cos(w0)
        sin_w0 = math.sin(w0)
        alpha = sin_w0 / (2.0 * math.sqrt(2.0))  # Q = 1/√2 for Butterworth

        b0 = (1.0 + cos_w0) / 2.0
        b1 = -(1.0 + cos_w0)
        b2 = (1.0 + cos_w0) / 2.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha

        return (b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

    def _apply_highpass(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply the biquad high-pass filter using Direct Form II transposed.

        Maintains z1/z2 state across calls so the filter is continuous
        across chunk boundaries (no clicks or transients at seams).
        """
        b0, b1, b2, a1, a2 = self._hpf_coeffs
        out = np.empty_like(audio)
        z1, z2 = self._hpf_z1, self._hpf_z2

        for i in range(len(audio)):
            x = float(audio[i])
            y = b0 * x + z1
            z1 = b1 * x - a1 * y + z2
            z2 = b2 * x - a2 * y
            out[i] = y

        self._hpf_z1, self._hpf_z2 = z1, z2
        return out

    # ── Stage 2: Noise gate ───────────────────────────────────────────────────

    def _apply_noise_gate(self, audio: np.ndarray) -> np.ndarray:
        """
        Simple RMS-based noise gate with soft attenuation.

        Below-threshold audio is attenuated by NOISE_GATE_ATTENUATION (-40 dB)
        rather than hard-zeroed, which avoids audible clicks at gate
        open/close transitions.
        """
        rms = float(np.sqrt(np.mean(audio**2)))
        if rms < self.NOISE_GATE_THRESHOLD:
            return audio * self.NOISE_GATE_ATTENUATION
        return audio

    # ── Stage 3: Automatic Gain Control ───────────────────────────────────────

    def _apply_agc(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalise volume with EMA-smoothed gain.

        Quiet audio is amplified toward AGC_TARGET_RMS, loud audio is
        compressed.  Gain changes are smoothed with an exponential moving
        average to prevent audible "pumping".
        """
        rms = float(np.sqrt(np.mean(audio**2)))
        if rms > 1e-6:
            desired_gain = self.AGC_TARGET_RMS / rms
            desired_gain = min(desired_gain, self.AGC_MAX_GAIN)
            self._agc_gain = (
                self.AGC_SMOOTHING * self._agc_gain
                + (1.0 - self.AGC_SMOOTHING) * desired_gain
            )
        return np.clip(audio * self._agc_gain, -1.0, 1.0)

    # ── Stage 4: Spectral denoise (optional) ──────────────────────────────────

    def _apply_spectral_denoise(self, audio: np.ndarray) -> np.ndarray:
        """
        Spectral gating via the ``noisereduce`` library.

        Lazy-imports the library so there is zero cost when disabled.
        Falls back gracefully (returns audio unchanged) if the library
        is not installed.
        """
        if self._nr_module is None:
            try:
                import noisereduce as nr

                self._nr_module = nr
                logger.info("noisereduce loaded — spectral denoising active")
            except ImportError:
                logger.warning(
                    "noisereduce not installed — spectral denoising disabled. "
                    "Install with: pip install noisereduce"
                )
                self._enable_spectral = False
                return audio

        return self._nr_module.reduce_noise(  # type: ignore[union-attr]
            y=audio,
            sr=self.sample_rate,
            stationary=True,
            prop_decrease=0.75,
        )
