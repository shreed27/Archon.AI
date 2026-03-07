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
    regional: bool = False,
    language: str = "hi-IN",
) -> None:
    """
    Start a J.A.R.V.I.S. voice session.
    """
    from archon.cli.ui import ArchonUI
    from archon.manager.orchestrator import ManagerOrchestrator

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

    live_client = None
    if regional:
        console.print(
            f"[bold color(201)]🇮🇳  AI FOR BHARAT MODE ACTIVATED ({language})[/bold color(201)]"
        )

        # Initialize Manager Orchestrator for AWS Brain
        manager = ManagerOrchestrator(str(project_path))
        await manager.initialize()

        from archon.voice.aws_live_client import AWSLiveClient

        live_client = AWSLiveClient(manager, language_code=language)

        # Verify AWS credentials
        if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
            console.print(
                "[yellow]Warning: AWS credentials not found in environment. STT/TTS may fail.[/yellow]"
            )
    else:
        # Check Gemini API key early
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            console.print(
                "\n[bold red]🔑 GOOGLE_API_KEY not set.[/bold red]\n"
                "Voice mode requires a Google API key with billing enabled.\n"
            )
            # Fall back to text REPL
            from archon.cli.commands import start_command

            start_command(project_path)
            return

    # Import here to avoid circular deps
    from archon.voice.voice_session import VoiceSession

    session = VoiceSession(
        project_path=project_path,
        activation=activation_mode,
        voice_name=voice_name,
        live_client=live_client,
    )
    await session.run()
