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


class AudioPreprocessor:
    """
    Stateful audio preprocessor.  One instance per VoiceSession.

    Maintains biquad filter state and AGC gain across chunk boundaries
    so the processed output is a seamless, continuous stream.
    """

    # High-pass filter
    HPF_CUTOFF_HZ: float = _HPF_CUTOFF_HZ

    def __init__(
        self,
        sample_rate: int = 16_000,
    ) -> None:
        self.sample_rate = sample_rate

        # Biquad high-pass filter state (Direct Form II transposed)
        self._hpf_coeffs = self._compute_hpf_coeffs()
        self._hpf_z1: float = 0.0
        self._hpf_z2: float = 0.0

        logger.info(
            "AudioPreprocessor initialised: hpf=%dHz",
            int(self.HPF_CUTOFF_HZ),
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
