"""
CLI command for the J.A.R.V.I.S. voice session.

Registered as `archon voice <path>` via __main__.py.
"""

import os
from pathlib import Path

from rich.console import Console

from archon.cli.session_config import VoiceActivation

console = Console()


async def voice_command(
    project_path: Path,
    activation: str = "vad",
    voice_name: str = "Puck",
) -> None:
    """
    Start a J.A.R.V.I.S. voice session.

    Args:
        project_path: Absolute path to the project directory.
        activation:   Activation mode string: 'vad' | 'ptt' | 'wake'.
        voice_name:   Gemini voice persona (default: env ARCHON_VOICE or 'Puck').
    """
    from archon.cli.ui import ArchonUI

    # Show the normal header
    ArchonUI.print_header(project_path.name)

    # Resolve voice name from env if not explicitly provided
    voice_name = voice_name or os.getenv("ARCHON_VOICE", "Puck")

    # Map CLI string to enum
    activation_mode_map = {
        "vad": VoiceActivation.VAD,
        "ptt": VoiceActivation.PTT,
        "wake": VoiceActivation.WAKE_WORD,
    }
    activation_mode = activation_mode_map.get(activation.lower(), VoiceActivation.VAD)

    # Check API key early and give a clear error
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print(
            "\n[bold red]🔑 GOOGLE_API_KEY not set.[/bold red]\n"
            "Voice mode requires a Google API key with billing enabled.\n\n"
            "  [bold]Set it:[/bold]  export GOOGLE_API_KEY='AIza...'\n"
            "  [bold]Or:[/bold]     add it to your .env file\n\n"
            "[dim]Falling back to text REPL...[/dim]\n"
        )
        # Fall back to the normal text REPL
        from archon.cli.commands import start_command

        await start_command(project_path)
        return

    # Import here to avoid circular deps and optional-import issues at module load
    from archon.voice.voice_session import VoiceSession

    session = VoiceSession(
        project_path=project_path,
        activation=activation_mode,
        voice_name=voice_name,
        api_key=api_key,
    )
    await session.run()
