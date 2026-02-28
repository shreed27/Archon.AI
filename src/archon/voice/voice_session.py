"""
VoiceSession — J.A.R.V.I.S. Voice Interface Orchestrator.

Wires together all voice components:
  • GenaiLiveClient   — Gemini Live API WebSocket
  • MicCapture        — async microphone input
  • SpeakerPlayback   — async speaker output
  • _BaseActivator    — VAD / PTT / WakeWord activation logic
  • WaveformVisualizer — animated terminal UI

Conversation loop (VAD mode):
  ┌─────────────────────────────────────────────────────┐
  │  [LISTENING]  Mic → Gemini (continuous stream)       │
  │      ↓  Gemini responds                             │
  │  [THINKING]   Wait for first audio chunk            │
  │      ↓                                              │
  │  [SPEAKING]   Play audio chunks from Gemini         │
  │      ↓  Audio ends or barge-in detected             │
  │  [LISTENING]  Back to listening                     │
  └─────────────────────────────────────────────────────┘

PTT / WakeWord mode:
  Mic is gated by ActivationEvent.LISTENING_START → LISTENING_END.
  Between turns the mic capture still runs but audio is not forwarded.

Slash commands (typed in the terminal even in voice mode):
  /activation  — Switch VAD | PTT | WakeWord
  /voice       — Cycle Gemini voice persona
  /text        — Drop back to the standard text REPL
  /exit        — Quit
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from archon.cli.session_config import VoiceActivation
from archon.voice.activation import (
    ActivationEvent,
    WakeWordActivator,
    build_activator,
)
from archon.voice.audio_io import (
    AudioInputError,
    AudioOutputError,
    MicCapture,
    SpeakerPlayback,
    compute_rms,
)
from archon.voice.audio_processing import AudioPreprocessor
from archon.voice.gemini_live_client import (
    GenaiLiveClient,
    LiveAPIKeyError,
    LiveAPIUnavailableError,
    LiveSession,
)
from archon.voice.visualizer import VisualizerState, WaveformVisualizer

logger = logging.getLogger(__name__)

console = Console()

# Barge-in: if mic RMS stays above this while agent is speaking, interrupt
BARGE_IN_RMS_THRESHOLD = 0.04
BARGE_IN_FRAMES_REQUIRED = 4  # ~0.4 s of sustained speech

# Available voice personas (for /voice cycling)
VOICE_PERSONAS = ["Puck", "Kore", "Aoede", "Charon", "Fenrir"]


# ── VoiceSession ──────────────────────────────────────────────────────────────


class VoiceSession:
    """
    Orchestrates a hands-free J.A.R.V.I.S.-style voice session.

    Args:
        project_path: Path to the project directory.
        activation:   VoiceActivation mode (VAD, PTT, WAKE_WORD).
        voice_name:   Gemini voice persona name.
        api_key:      Google API key (defaults to GOOGLE_API_KEY env var).
    """

    def __init__(
        self,
        project_path: Path,
        activation: VoiceActivation = VoiceActivation.VAD,
        voice_name: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.project_path = project_path
        self.activation_mode = activation
        self.voice_name = voice_name or os.getenv("ARCHON_VOICE", "Puck")
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        # Runtime state
        self._running = True
        self._voice_idx = (
            VOICE_PERSONAS.index(self.voice_name) if self.voice_name in VOICE_PERSONAS else 0
        )

    # ── Public entrypoint ──────────────────────────────────────────────────

    async def run(self) -> None:
        """
        Start the voice session. This is the main entry point.

        Handles startup errors gracefully — if the API key is missing or
        audio devices are unavailable, a friendly message is printed and
        the method returns cleanly.
        """
        self._print_welcome()

        try:
            await self._main_loop()
        except LiveAPIKeyError as exc:
            console.print(f"\n[bold red]🔑 API Key Error:[/bold red] {exc}")
            console.print("[dim]Falling back to text mode. Run 'archon start .' to continue.[/dim]")
        except LiveAPIUnavailableError as exc:
            console.print(f"\n[bold red]📦 Import Error:[/bold red] {exc}")
        except AudioInputError as exc:
            console.print(f"\n[bold red]🎙️ Microphone Error:[/bold red] {exc}")
        except AudioOutputError as exc:
            console.print(f"\n[bold red]🔊 Speaker Error:[/bold red] {exc}")
        except KeyboardInterrupt:
            pass
        finally:
            console.print("\n[bold cyan]👋 Voice session ended. Goodbye, boss.[/bold cyan]\n")

    # ── Internal main loop ─────────────────────────────────────────────────

    async def _main_loop(self) -> None:
        """Core conversation loop."""
        client = GenaiLiveClient(
            api_key=self.api_key,
            voice_name=self.voice_name,
        )
        activator = build_activator(self.activation_mode)

        # Audio preprocessing: HPF → noise gate → AGC → (optional) spectral denoise
        preprocessor = AudioPreprocessor(
            enable_spectral_denoise=os.getenv("ARCHON_NOISE_REDUCE", "0") == "1",
        )
        logger.info("Audio preprocessor ready")

        async with (
            WaveformVisualizer() as viz,
            MicCapture() as mic,
            SpeakerPlayback() as speaker,
        ):
            await activator.start()

            slash_task = asyncio.create_task(self._watch_slash_commands(viz))

            viz.set_state(VisualizerState.LISTENING)

            try:
                async with client.session() as sess:
                    # Concurrent tasks
                    mic_fwd_task = asyncio.create_task(
                        self._mic_forward_loop(mic, activator, viz, sess, preprocessor)
                    )
                    recv_task = asyncio.create_task(self._receive_loop(sess, speaker, viz))

                    await asyncio.gather(mic_fwd_task, recv_task, slash_task)

            finally:
                slash_task.cancel()
                await activator.stop()

    # ── Mic forwarding task ────────────────────────────────────────────────

    async def _mic_forward_loop(
        self,
        mic: MicCapture,
        activator,
        viz: WaveformVisualizer,
        sess: LiveSession,
        preprocessor: AudioPreprocessor,
    ) -> None:
        """
        Continuously reads from mic, preprocesses, and forwards to Gemini.

        Audio flow:
          raw chunk → compute_rms (for viz + barge-in on RAW signal)
                    → preprocessor.process (HPF → gate → AGC → spectral)
                    → sess.send_audio (clean audio to Gemini)
        """
        forwarding = self.activation_mode == VoiceActivation.VAD
        barge_in_streak = 0

        async for chunk in mic:
            if not self._running:
                break

            # RMS from RAW audio — visualiser and barge-in need real mic levels
            rms = compute_rms(chunk)
            viz.push_mic_rms(rms)

            # Feed RMS to wake-word activator if in that mode
            if isinstance(activator, WakeWordActivator):
                activator.push_rms(rms)

            # Check for activation events (non-blocking)
            while not activator._events.empty():
                event = activator._events.get_nowait()
                if event == ActivationEvent.LISTENING_START:
                    forwarding = True
                    viz.set_state(VisualizerState.LISTENING)
                    sess.clear_interrupt()
                elif event == ActivationEvent.LISTENING_END:
                    forwarding = False
                    await sess.end_turn()
                    viz.set_state(VisualizerState.THINKING)
                elif event in (ActivationEvent.EXIT,):
                    self._running = False
                    return

            # Barge-in detection: loud mic while speaker is playing
            if viz._state == VisualizerState.SPEAKING:
                if rms > BARGE_IN_RMS_THRESHOLD:
                    barge_in_streak += 1
                    if barge_in_streak >= BARGE_IN_FRAMES_REQUIRED:
                        sess.interrupt()
                        viz.set_state(VisualizerState.LISTENING)
                        barge_in_streak = 0
                        logger.debug("Barge-in triggered (RMS=%.3f)", rms)
                else:
                    barge_in_streak = 0

            # Preprocess and forward to Gemini
            if forwarding:
                clean_chunk = preprocessor.process(chunk)
                await sess.send_audio(clean_chunk)

    # ── Receive loop task ──────────────────────────────────────────────────

    async def _receive_loop(
        self,
        sess: LiveSession,
        speaker: SpeakerPlayback,
        viz: WaveformVisualizer,
    ) -> None:
        """Receives audio/text from Gemini and plays it."""
        while self._running:
            async for part in sess.receive():
                if not self._running:
                    break

                if part.is_final:
                    # Turn complete — go back to listening
                    viz.set_state(VisualizerState.LISTENING)
                    if self.activation_mode == VoiceActivation.VAD:
                        sess.clear_interrupt()
                    break

                if part.audio:
                    if viz._state != VisualizerState.SPEAKING:
                        viz.set_state(VisualizerState.SPEAKING)
                    # Check barge-in flag
                    if sess._interrupted.is_set():
                        speaker.clear()
                        sess.clear_interrupt()
                        viz.set_state(VisualizerState.LISTENING)
                        break
                    rms = compute_rms(part.audio)
                    viz.push_speaker_rms(rms)
                    await speaker.play(part.audio)

                elif part.text:
                    # Show text transcription subtly
                    console.print(f"\n[dim italic]Archon: {part.text}[/dim italic]", end="\r")

    # ── Slash command watcher (runs in background task) ────────────────────

    async def _watch_slash_commands(self, viz: WaveformVisualizer) -> None:
        """
        Reads stdin for slash commands typed during a voice session.
        Runs in a separate asyncio task so it doesn't block audio.
        """
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                # stdin read in executor to avoid blocking the event loop
                line = await loop.run_in_executor(None, sys.stdin.readline)
            except (EOFError, OSError):
                break

            cmd = line.strip().lower()

            if cmd in ("/exit", "/quit", "exit", "quit"):
                self._running = False
                break

            elif cmd == "/voice":
                self._voice_idx = (self._voice_idx + 1) % len(VOICE_PERSONAS)
                self.voice_name = VOICE_PERSONAS[self._voice_idx]
                console.print(
                    f"\n[bold color(201)]🎙  Voice changed to {self.voice_name}[/bold color(201)]"
                    "\n[dim]Takes effect on next session restart.[/dim]\n"
                )

            elif cmd == "/text":
                console.print("\n[bold cyan]Switching to text mode...[/bold cyan]")
                self._running = False
                break

            elif cmd == "/activation":
                modes = list(VoiceActivation)
                cur_idx = modes.index(self.activation_mode)
                self.activation_mode = modes[(cur_idx + 1) % len(modes)]
                console.print(
                    f"\n[bold color(82)]✓ Activation mode → {self.activation_mode.value}[/bold color(82)]"
                    "\n[dim]Takes effect on next session restart.[/dim]\n"
                )

            elif cmd == "/help":
                console.print(
                    Panel(
                        "  [bold color(201)]/voice[/bold color(201)]      — Cycle voice persona (Puck→Kore→Aoede→Charon→Fenrir)\n"
                        "  [bold color(39)]/activation[/bold color(39)] — Switch activation mode (VAD→PTT→WakeWord)\n"
                        "  [bold white]/text[/bold white]       — Return to text REPL\n"
                        "  [bold white]/exit[/bold white]       — Quit Archon voice session",
                        title="[bold]Voice Commands[/bold]",
                        border_style="color(201)",
                    )
                )

    # ── Welcome banner ─────────────────────────────────────────────────────

    def _print_welcome(self) -> None:
        """Print the J.A.R.V.I.S. voice mode welcome banner."""
        from archon.cli.session_config import VOICE_ACTIVATION_METADATA

        act_meta = VOICE_ACTIVATION_METADATA[self.activation_mode]
        console.print(
            Panel(
                f"[bold color(201)]  🎙️  J.A.R.V.I.S. MODE ACTIVATED[/bold color(201)]\n\n"
                f"  [bold white]Voice:[/bold white]      [bold color(39)]{self.voice_name}[/bold color(39)]\n"
                f"  [bold white]Activation:[/bold white] [bold color(39)]{act_meta['icon']} {act_meta['label']}[/bold color(39)]\n"
                f"  [bold white]Model:[/bold white]      [dim]gemini-2.0-flash-live-001[/dim]\n\n"
                f"  [dim]Type /help for voice commands · Ctrl+C to exit[/dim]",
                title="[bold color(201)] ARCHON VOICE [/bold color(201)]",
                border_style="color(201)",
                padding=(1, 4),
            )
        )
        console.print()

        if self.activation_mode == VoiceActivation.PTT:
            console.print(
                "  [bold color(226)]Hold SPACE to speak, release to send.[/bold color(226)]\n"
            )
        elif self.activation_mode == VoiceActivation.WAKE_WORD:
            console.print(
                "  [bold color(226)]Say 'Hey Archon' to start a turn.[/bold color(226)]\n"
            )
        else:
            console.print(
                "  [bold color(226)]Start speaking — Archon is always listening.[/bold color(226)]\n"
            )
