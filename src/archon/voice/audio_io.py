"""
Audio I/O — microphone capture and speaker playback.

Uses `sounddevice` for cross-platform, low-latency audio streaming.
Designed for the Gemini Live API format:
  - Input:   16 kHz, mono, 16-bit PCM (LINEAR16)
  - Output:  24 kHz, mono, 16-bit PCM (LINEAR16)

Classes:
    MicCapture      — async generator yielding raw PCM chunks from the mic.
    SpeakerPlayback — async queue-based PCM playback.
    AudioInputError — raised when no input device is available.
    AudioOutputError — raised when no output device is available.

Environment overrides:
    ARCHON_VOICE_SAMPLE_RATE   (default 16000)
    ARCHON_VOICE_PLAYBACK_RATE (default 24000)
"""

import asyncio
import os
import queue
import struct
from typing import AsyncIterator

import numpy as np

try:
    import sounddevice as sd
except ImportError:  # pragma: no cover
    sd = None  # type: ignore[assignment]


# ── Configuration ─────────────────────────────────────────────────────────────

MIC_SAMPLE_RATE: int = int(os.getenv("ARCHON_VOICE_SAMPLE_RATE", "16000"))
SPEAKER_SAMPLE_RATE: int = int(os.getenv("ARCHON_VOICE_PLAYBACK_RATE", "24000"))

# Chunk duration in seconds — 100 ms is a sweet spot for latency vs. overhead
CHUNK_DURATION_S: float = 0.1
MIC_CHUNK_FRAMES: int = int(MIC_SAMPLE_RATE * CHUNK_DURATION_S)
SPEAKER_CHUNK_FRAMES: int = int(SPEAKER_SAMPLE_RATE * CHUNK_DURATION_S)

DTYPE = np.int16
BYTES_PER_SAMPLE = 2  # int16 = 2 bytes


# ── Custom exceptions ─────────────────────────────────────────────────────────


class AudioInputError(RuntimeError):
    """Raised when the microphone cannot be opened."""


class AudioOutputError(RuntimeError):
    """Raised when the speaker cannot be opened."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _check_sounddevice() -> None:
    """Raise ImportError with a helpful message if sounddevice is not installed."""
    if sd is None:
        raise ImportError(
            "sounddevice is required for voice mode.\n"
            "Install with:  poetry install\n"
            "Also ensure portaudio is installed:  brew install portaudio"
        )


def compute_rms(pcm_bytes: bytes) -> float:
    """
    Compute the root-mean-square amplitude of a PCM chunk.

    Returns a value in [0.0, 1.0] where 1.0 is full scale (32768 peak).
    Used by the waveform visualizer to drive bar heights.
    """
    if len(pcm_bytes) < 2:
        return 0.0
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    if samples.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(samples**2)))
    return min(rms / 32768.0, 1.0)


def pcm_bytes_to_np(pcm_bytes: bytes) -> np.ndarray:
    """Convert raw PCM bytes to a float32 numpy array in [-1, 1]."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return arr / 32768.0


def np_to_pcm_bytes(arr: np.ndarray) -> bytes:
    """Convert a float32 numpy array in [-1, 1] back to int16 PCM bytes."""
    arr = np.clip(arr, -1.0, 1.0)
    return (arr * 32767).astype(np.int16).tobytes()


# ── MicCapture ────────────────────────────────────────────────────────────────


class MicCapture:
    """
    Async generator that continuously captures microphone input.

    Usage:
        async with MicCapture() as mic:
            async for chunk in mic:
                await live_client.send_audio(chunk)

    Each yielded chunk is a `bytes` object containing LINEAR16 PCM data
    at MIC_SAMPLE_RATE (default 16 kHz), mono channel.
    """

    def __init__(self, sample_rate: int = MIC_SAMPLE_RATE) -> None:
        _check_sounddevice()
        self.sample_rate = sample_rate
        self._q: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._stream: "sd.InputStream | None" = None
        self._loop: asyncio.AbstractEventLoop | None = None

    # ── Context manager ────────────────────────────────────────────────────

    async def __aenter__(self) -> "MicCapture":
        self._loop = asyncio.get_running_loop()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=MIC_CHUNK_FRAMES,
            callback=self._callback,
        )
        try:
            self._stream.start()
        except sd.PortAudioError as exc:
            raise AudioInputError(
                f"Could not open microphone: {exc}\n"
                "Make sure a microphone is connected and accessible."
            ) from exc
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
        # Signal the async iterator to stop
        await self._q.put(None)

    # ── sounddevice callback (runs in a C thread) ──────────────────────────

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time: object,
        status: object,
    ) -> None:
        """Called by sounddevice for each audio block. Thread-safe."""
        if self._loop is None:
            return
        pcm = indata.copy().tobytes()
        # Schedule a put on the event-loop thread
        self._loop.call_soon_threadsafe(self._q.put_nowait, pcm)

    # ── Async iterator ─────────────────────────────────────────────────────

    def __aiter__(self) -> "MicCapture":
        return self

    async def __anext__(self) -> bytes:
        chunk = await self._q.get()
        if chunk is None:
            raise StopAsyncIteration
        return chunk


# ── SpeakerPlayback ───────────────────────────────────────────────────────────


class SpeakerPlayback:
    """
    Async queue-based speaker playback.

    Usage:
        async with SpeakerPlayback() as speaker:
            async for audio_chunk in live_client.recv_audio():
                await speaker.play(audio_chunk)

    Audio chunks are queued and played in order via a background task to
    avoid blocking the recv loop.
    """

    def __init__(self, sample_rate: int = SPEAKER_SAMPLE_RATE) -> None:
        _check_sounddevice()
        self.sample_rate = sample_rate
        self._q: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._stream: "sd.OutputStream | None" = None
        self._task: asyncio.Task | None = None  # type: ignore[type-arg]
        self.is_playing: bool = False

    async def __aenter__(self) -> "SpeakerPlayback":
        self._stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
        )
        try:
            self._stream.start()
        except sd.PortAudioError as exc:
            raise AudioOutputError(f"Could not open speaker: {exc}") from exc
        self._task = asyncio.create_task(self._drain_loop())
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._q.put(None)  # sentinel to stop drain loop
        if self._task:
            await self._task
        if self._stream:
            self._stream.stop()
            self._stream.close()

    async def play(self, pcm_bytes: bytes) -> None:
        """Queue a PCM chunk for playback (non-blocking)."""
        await self._q.put(pcm_bytes)

    async def drain(self) -> None:
        """Wait until the playback queue is empty."""
        await self._q.join()

    def clear(self) -> None:
        """Discard all queued audio (use for barge-in / interruption)."""
        while not self._q.empty():
            try:
                self._q.get_nowait()
                self._q.task_done()
            except asyncio.QueueEmpty:
                break
        self.is_playing = False

    async def _drain_loop(self) -> None:
        """Background task that writes queued chunks to the OutputStream."""
        if self._stream is None:
            return
        while True:
            chunk = await self._q.get()
            if chunk is None:
                self._q.task_done()
                break
            self.is_playing = True
            arr = np.frombuffer(chunk, dtype=np.int16)
            self._stream.write(arr)
            self._q.task_done()
        self.is_playing = False
