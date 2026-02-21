"""
Waveform Visualizer — animated terminal waveform for voice states.

Uses Rich's Live display to render a constantly-updating bar chart in
the terminal that reflects the current audio state.

States:
  LISTENING  — Green bars driven by mic RMS
  THINKING   — Cyan spinner (no audio data, agent is processing)
  SPEAKING   — Blue bars driven by playback RMS

The visualizer runs as a background asyncio Task and is updated by
feeding RMS values via push_mic_rms() / push_speaker_rms().
The caller controls state transitions with set_state().
"""

import asyncio
import math
import time
from enum import Enum, auto
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

console = Console()

# ── State enum ────────────────────────────────────────────────────────────────


class VisualizerState(Enum):
    IDLE = auto()  # Not in a voice turn
    LISTENING = auto()  # Mic is open and streaming
    THINKING = auto()  # Waiting for Gemini response
    SPEAKING = auto()  # Agent is playing audio


# ── Bar character table ────────────────────────────────────────────────────────

_BAR_CHARS = " ▁▂▃▄▅▆▇█"
_N_BARS = 24  # Number of bars across the waveform panel
_FPS = 10  # Target frames per second for the live update
_FRAME_S = 1.0 / _FPS


def _rms_to_bar(rms: float, phase_offset: float = 0.0) -> str:
    """
    Convert an RMS value [0, 1] to a string of Unicode block characters.

    A sin-wave envelope is applied across the bar positions to give the
    waveform its oscillating shape.  `phase_offset` advances the wave
    each frame to create animation.
    """
    chars = []
    for i in range(_N_BARS):
        # Standing-wave envelope: each bar's height modulated by a sin
        envelope = 0.5 + 0.5 * math.sin(math.pi * i / _N_BARS + phase_offset)
        level = rms * envelope
        idx = min(int(level * (len(_BAR_CHARS) - 1)), len(_BAR_CHARS) - 1)
        chars.append(_BAR_CHARS[idx])
    return "".join(chars)


# ── Visualizer ────────────────────────────────────────────────────────────────


class WaveformVisualizer:
    """
    Manages a Rich Live block that shows an animated audio waveform.

    Usage::

        async with WaveformVisualizer() as viz:
            viz.set_state(VisualizerState.LISTENING)
            # In the mic capture loop:
            viz.push_mic_rms(rms_value)
            # When agent speaks:
            viz.set_state(VisualizerState.SPEAKING)
            viz.push_speaker_rms(rms_value)
    """

    def __init__(self) -> None:
        self._state: VisualizerState = VisualizerState.IDLE
        self._mic_rms: float = 0.0
        self._speaker_rms: float = 0.0
        self._phase: float = 0.0
        self._live: Optional[Live] = None
        self._task: Optional[asyncio.Task] = None  # type: ignore[type-arg]

    # ── Context manager ────────────────────────────────────────────────────

    async def __aenter__(self) -> "WaveformVisualizer":
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=_FPS,
            transient=False,
        )
        self._live.__enter__()
        self._task = asyncio.create_task(self._animation_loop())
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._live:
            self._live.__exit__(None, None, None)

    # ── State control ──────────────────────────────────────────────────────

    def set_state(self, state: VisualizerState) -> None:
        """Switch the displayed state (thread-safe, call from event loop)."""
        self._state = state
        if state != VisualizerState.LISTENING:
            self._mic_rms = 0.0
        if state != VisualizerState.SPEAKING:
            self._speaker_rms = 0.0

    def push_mic_rms(self, rms: float) -> None:
        """Feed the latest mic RMS value from audio_io.compute_rms()."""
        self._mic_rms = rms

    def push_speaker_rms(self, rms: float) -> None:
        """Feed the latest speaker RMS value."""
        self._speaker_rms = rms

    # ── Rendering ──────────────────────────────────────────────────────────

    def _render(self) -> Panel:
        """Build the Rich renderable for the current state."""
        state = self._state

        if state == VisualizerState.LISTENING:
            bars = _rms_to_bar(max(self._mic_rms, 0.05), self._phase)
            content = Text(f"  {bars}  ", style="bold green")
            title = "🎙️  [bold green]LISTENING[/bold green]"
            border = "green"

        elif state == VisualizerState.THINKING:
            spinner = Spinner("dots", text="  Processing...  ", style="bold cyan")
            return Panel(
                spinner,
                title="⚙️  [bold cyan]THINKING[/bold cyan]",
                border_style="cyan",
                padding=(0, 2),
            )

        elif state == VisualizerState.SPEAKING:
            bars = _rms_to_bar(max(self._speaker_rms, 0.05), self._phase)
            content = Text(f"  {bars}  ", style="bold blue")
            title = "🔊  [bold blue]SPEAKING[/bold blue]"
            border = "blue"

        else:  # IDLE
            content = Text("  " + "─" * _N_BARS + "  ", style="dim white")
            title = "[dim]ARCHON VOICE — IDLE[/dim]"
            border = "dim white"

        return Panel(content, title=title, border_style=border, padding=(0, 2))

    # ── Animation loop ─────────────────────────────────────────────────────

    async def _animation_loop(self) -> None:
        """Advance the phase angle and refresh the display at _FPS."""
        while True:
            await asyncio.sleep(_FRAME_S)
            self._phase += 0.4  # Advance wave phase for animation
            if self._live:
                self._live.update(self._render())
