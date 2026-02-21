"""
Gemini Live API Client.

Wraps the `google.genai` Live API to provide a clean async interface for
bidirectional real-time audio streaming with Gemini.

Model: gemini-2.0-flash-live-001  (billing must be enabled)

Session lifecycle:
  1. Call `async with GenaiLiveClient(...) as session:` to open a WebSocket.
  2. Send mic audio with `await session.send_audio(chunk)`.
  3. Receive audio/text responses via `async for part in session.receive():`.
  4. For barge-in: call `session.interrupt()` — queues a graceful cancel signal.

Voice personas (ARCHON_VOICE env or voice_name arg):
  Puck   — energetic and clear (default)
  Kore   — warm and friendly
  Aoede  — calm and focused
  Charon — deep and authoritative
  Fenrir — dynamic and expressive

System prompt is optimised for spoken J.A.R.V.I.S.-style responses:
  - Concise (max 3 sentences unless asked for detail)
  - No markdown in output
  - Direct, confident tone
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

# google.genai is the new unified SDK (google-genai package)
try:
    import google.genai as genai
    from google.genai import types as genai_types

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False  # type: ignore[assignment]
    genai = None  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]

from archon.voice.response_formatter import format_for_speech

# ── Constants ─────────────────────────────────────────────────────────────────

LIVE_MODEL = "gemini-2.0-flash-live-001"

# Gemini Live API audio formats
MIC_SAMPLE_RATE = int(os.getenv("ARCHON_VOICE_SAMPLE_RATE", "16000"))
SPEAKER_SAMPLE_RATE = int(os.getenv("ARCHON_VOICE_PLAYBACK_RATE", "24000"))

JARVIS_SYSTEM_PROMPT = """You are Archon, an advanced AI coding partner — think J.A.R.V.I.S. for software development.

Your voice response rules (CRITICAL — always follow these):
1. NEVER use markdown syntax in your replies (no **, *, #, backticks, bullet points).
2. Speak in complete but concise sentences. Maximum 3 sentences unless the user asks for detail.
3. Lead with the answer, then brief context if needed.
4. Use natural spoken language: say "function" not "func", "directory" not "dir".
5. For code, describe what it does verbally rather than reciting it line by line.
6. Be direct, confident, and helpful — like a senior engineer pair-programming with you.
7. If you need to show code or long output, say "I've prepared the code — check the terminal."
"""


# ── Exceptions ────────────────────────────────────────────────────────────────


class LiveAPIUnavailableError(RuntimeError):
    """Raised when google-genai package is not installed."""


class LiveAPIKeyError(ValueError):
    """Raised when GOOGLE_API_KEY is missing."""


# ── Response part ─────────────────────────────────────────────────────────────


class ResponsePart:
    """
    A single chunk from the Gemini Live API response stream.

    Exactly one of `audio` or `text` will be set, never both.
    """

    __slots__ = ("audio", "text", "is_final")

    def __init__(
        self,
        audio: Optional[bytes] = None,
        text: Optional[str] = None,
        is_final: bool = False,
    ) -> None:
        self.audio = audio
        self.text = text
        self.is_final = is_final

    def __repr__(self) -> str:  # pragma: no cover
        if self.audio:
            return f"<ResponsePart audio={len(self.audio)}bytes final={self.is_final}>"
        return f"<ResponsePart text={self.text!r} final={self.is_final}>"


# ── Live session handle ────────────────────────────────────────────────────────


class LiveSession:
    """
    Handle to an active Gemini Live WebSocket session.

    Obtained via `async with GenaiLiveClient.session() as sess`.
    """

    def __init__(self, raw_session: object, interrupted: asyncio.Event) -> None:
        self._sess = raw_session
        self._interrupted = interrupted

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """
        Stream a raw PCM audio chunk to Gemini.

        Args:
            pcm_bytes: LINEAR16, mono, 16 kHz PCM bytes.
        """
        if self._interrupted.is_set():
            return  # Drop input during an interruption
        await self._sess.send(input=genai_types.LiveClientRealtimeInput(audio=pcm_bytes))

    async def end_turn(self) -> None:
        """Signal end of the user's speech turn (used in PTT/WakeWord mode)."""
        await self._sess.send(input=genai_types.LiveClientRealtimeInput(audio_stream_end=True))

    async def send_text(self, text: str) -> None:
        """
        Send a text message instead of audio (useful for hybrid mode).

        The text is appended to the conversation as a user turn.
        """
        await self._sess.send(input=text, end_of_turn=True)

    def interrupt(self) -> None:
        """
        Signal a barge-in interruption.

        Sets the interrupted flag so audio is dropped while the session
        resets.  The VoiceSession is responsible for draining the speaker
        queue and re-entering the listening state.
        """
        self._interrupted.set()

    def clear_interrupt(self) -> None:
        """Clear the interruption flag to resume normal operation."""
        self._interrupted.clear()

    async def receive(self) -> AsyncIterator[ResponsePart]:
        """
        Async iterator over response parts from Gemini.

        Yields ResponsePart objects containing either audio bytes or text.
        Raises StopAsyncIteration when the turn is complete (is_final=True).
        """
        async for server_content in self._sess.receive():
            # Handle server-sent interruption signal
            if hasattr(server_content, "interrupted") and server_content.interrupted:
                yield ResponsePart(is_final=True)
                return

            model_turn = getattr(server_content, "server_content", None)
            if model_turn is None:
                model_turn = server_content  # some SDK versions flatten this

            parts = getattr(model_turn, "parts", None) or []
            for part in parts:
                # Audio chunk
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    yield ResponsePart(audio=inline_data.data)

                # Text chunk (fallback / transcript)
                text = getattr(part, "text", None)
                if text:
                    yield ResponsePart(text=format_for_speech(text))

            # End of turn signal
            turn_complete = getattr(model_turn, "turn_complete", False)
            if turn_complete:
                yield ResponsePart(is_final=True)
                return


# ── Client ────────────────────────────────────────────────────────────────────


class GenaiLiveClient:
    """
    Manager for Gemini Live API sessions.

    Usage::

        client = GenaiLiveClient(api_key=os.getenv("GOOGLE_API_KEY"), voice="Puck")
        async with client.session() as sess:
            await sess.send_audio(mic_chunk)
            async for part in sess.receive():
                if part.audio:
                    await speaker.play(part.audio)

    A single GenaiLiveClient can open multiple sequential sessions
    (one per conversation turn in PTT/WakeWord mode) but should not
    open concurrent sessions.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_name: str = "Puck",
        model: str = LIVE_MODEL,
    ) -> None:
        if not _GENAI_AVAILABLE:
            raise LiveAPIUnavailableError(
                "google-genai package is not installed.\n" "Run: poetry install"
            )
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self._api_key:
            raise LiveAPIKeyError(
                "GOOGLE_API_KEY is required for voice mode.\n"
                "Set it with: export GOOGLE_API_KEY='your-key'\n"
                "Or add it to your .env file."
            )
        self._voice_name = voice_name or os.getenv("ARCHON_VOICE", "Puck")
        self._model = model
        self._client = genai.Client(api_key=self._api_key)

    def _build_config(self) -> "genai_types.LiveConnectConfig":
        """Build the LiveConnectConfig with system prompt, voice, and VAD settings."""
        return genai_types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=JARVIS_SYSTEM_PROMPT,
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=self._voice_name,
                    )
                )
            ),
            realtime_input_config=genai_types.RealtimeInputConfig(
                automatic_activity_detection=genai_types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=0.7,
                    end_of_speech_sensitivity=0.6,
                    silence_duration_ms=800,
                    prefix_padding_ms=100,
                )
            ),
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[LiveSession]:
        """
        Open a new Live API WebSocket session.

        Use as::

            async with client.session() as sess:
                ...
        """
        interrupted = asyncio.Event()
        config = self._build_config()
        async with self._client.aio.live.connect(model=self._model, config=config) as raw_sess:
            yield LiveSession(raw_sess, interrupted)
