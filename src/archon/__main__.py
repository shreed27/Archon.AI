"""
Archon CLI Entrypoint.
"""

import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

from archon.cli.commands import start_command, resume_command, status_command

# Load environment variables (API keys etc.)
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Archon - AI Software Engineer")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start a new session")
    start_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Resume command
    resume_parser = subparsers.add_parser("resume", help="Resume existing session")
    resume_parser.add_argument("path", nargs="?", default=".", help="Project path")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show project status")
    status_parser.add_argument("path", nargs="?", default=".", help="Project path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    project_path = Path(args.path).resolve()

    try:
        if args.command == "start":
            asyncio.run(start_command(project_path))
        elif args.command == "resume":
            asyncio.run(resume_command(project_path))
        elif args.command == "status":
            asyncio.run(status_command(project_path))

    except KeyboardInterrupt:
        print("\n👋 Archon session terminated.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
