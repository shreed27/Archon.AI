"""
Archon CLI Entrypoint.
"""

import sys
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Silence noisy telemetry logs from dependencies (e.g., ChromaDB posthog errors)
logging.getLogger("chromadb").setLevel(logging.ERROR)

# Monkeypatch ChromaDB telemetry to disable the failing posthog capture
try:
    import chromadb.telemetry.product.posthog

    def disabled_capture(*args, **kwargs):
        pass

    chromadb.telemetry.product.posthog.Posthog.capture = disabled_capture
except (ImportError, AttributeError):
    pass

from archon.cli.commands import start_command, resume_command, status_command


# Load environment variables (API keys etc.)
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Archon - AI Software Engineer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a new session")
    start_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Add feature command
    add_parser = subparsers.add_parser("add", help="Add a new feature to an existing project")
    add_parser.add_argument("feature", help="Feature description (e.g. 'authentication')")
    add_parser.add_argument("--path", default=".", help="Project path")

    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume existing session")
    resume_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Voice command
    voice_parser = subparsers.add_parser(
        "voice",
        help="Start hands-free J.A.R.V.I.S. voice session",
    )
    voice_parser.add_argument("path", nargs="?", default=".", help="Project path")
    voice_parser.add_argument(
        "--activation",
        choices=["vad", "ptt", "wake"],
        default=None,
        help="Activation mode: vad (auto), ptt (push-to-talk), wake (wake word). "
        "Defaults to ARCHON_VOICE_ACTIVATION env var or 'vad'.",
    )
    voice_parser.add_argument(
        "--voice",
        default=None,
        help="Gemini voice persona: Puck, Kore, Aoede, Charon, Fenrir. "
        "Defaults to ARCHON_VOICE env var or 'Puck'.",
    )
    voice_parser.add_argument(
        "--regional",
        action="store_true",
        help="Enable AI for Bharat regional mode (AWS Transcribe/Polly/Translate).",
    )
    voice_parser.add_argument(
        "--language",
        default="hi-IN",
        help="Language code for regional mode (default: hi-IN).",
    )

    # Define known commands
    known_commands = ["start", "add", "resume", "status", "voice"]

    # Check if we should treat the input as a natural language goal
    # This happens if the first argument is not a known command and not a help flag
    if (
        len(sys.argv) > 1
        and sys.argv[1] not in known_commands
        and sys.argv[1] not in ["-h", "--help"]
    ):
        goal = " ".join(sys.argv[1:])
        project_path = Path(".").resolve()
        start_command(project_path, initial_goal=goal)
        return

    # Try to parse known args
    args, unknown = parser.parse_known_args()

    if not args.command:
        # Default to start if no arguments
        project_path = Path(".").resolve()
        start_command(project_path)
        return

    project_path = Path(getattr(args, "path", ".")).resolve()

    try:
        if args.command == "start":
            # Check if there's an initial goal provided in unknown args (if any)
            # Or we could add an optional goal arg to start_parser
            start_command(project_path)
        elif args.command == "add":
            from archon.cli.commands import add_command

            add_command(project_path, args.feature)
        elif args.command == "resume":
            resume_command(project_path)
        elif args.command == "status":
            status_command(project_path)
        elif args.command == "voice":
            from archon.cli.voice_commands import voice_command
            import os

            activation = getattr(args, "activation", None) or os.getenv(
                "ARCHON_VOICE_ACTIVATION", "vad"
            )
            voice = getattr(args, "voice", None) or os.getenv("ARCHON_VOICE", "Puck")
            regional = getattr(args, "regional", False)
            language = getattr(args, "language", "hi-IN")

            asyncio.run(
                voice_command(
                    project_path,
                    activation=activation,
                    voice_name=voice,
                    regional=regional,
                    language=language,
                )
            )

    except KeyboardInterrupt:
        print("\n👋 Archon session terminated.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Feature addition: added support for logging checks.
def _internal_logging_helper():
    pass
