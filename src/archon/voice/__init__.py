"""
Archon Voice Interface — J.A.R.V.I.S. mode.

Real-time, bidirectional voice conversation powered by the Gemini Live API.

Public surface:
    VoiceSession    — Main orchestrator; call VoiceSession.run() to start.
    VoiceActivation — Enum: VAD | PTT | WAKE_WORD
    ActivationEvent — Events emitted by the activation layer.

Quick start:
    >>> from archon.voice import VoiceSession
    >>> from archon.cli.session_config import VoiceActivation
    >>> session = VoiceSession(project_path, activation=VoiceActivation.VAD)
    >>> asyncio.run(session.run())
"""

from archon.voice.voice_session import VoiceSession  # noqa: F401

__all__ = ["VoiceSession"]
