"""
CLI entry point for ARCHON.

Usage:
    archon start
    archon resume
    archon status
"""

import asyncio
import click
from rich.console import Console
from pathlib import Path

from archon.cli.commands import start_command, resume_command, status_command
from archon.utils.logger import setup_logger

console = Console()
logger = setup_logger()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    ARCHON - Autonomous Engineering Organization CLI

    A distributed multi-agent AI engineering operating system.
    """
    pass


@cli.command()
@click.option("--project-path", default=".", help="Project directory path")
def start(project_path: str):
    """
    Start a new ARCHON project session.

    Example:
        archon start
        archon start --project-path ./my-project
    """
    console.print("[bold green]🚀 Starting ARCHON...[/bold green]")
    asyncio.run(start_command(Path(project_path)))


@cli.command()
@click.option("--project-path", default=".", help="Project directory path")
def resume(project_path: str):
    """
    Resume an existing ARCHON project session.

    Example:
        archon resume
    """
    console.print("[bold blue]🔄 Resuming ARCHON session...[/bold blue]")
    asyncio.run(resume_command(Path(project_path)))


@cli.command()
@click.option("--project-path", default=".", help="Project directory path")
def status(project_path: str):
    """
    Show current project status.

    Example:
        archon status
    """
    asyncio.run(status_command(Path(project_path)))


@cli.command()
@click.argument("scenario")
@click.option("--project-path", default=".", help="Project directory path")
def simulate(scenario: str, project_path: str):
    """
    Run simulation scenarios.

    Example:
        archon simulate "scale to 1M users"
    """
    from archon.simulation.scale_simulator import ScaleSimulator

    console.print(f"[bold yellow]🔬 Simulating: {scenario}[/bold yellow]")
    simulator = ScaleSimulator(Path(project_path))
    asyncio.run(simulator.run(scenario))


@cli.command()
@click.option("--project-path", default=".", help="Project directory path")
def chaos(project_path: str):
    """
    Run chaos engineering tests.

    Example:
        archon chaos test
    """
    from archon.simulation.chaos_engine import ChaosEngine

    console.print("[bold red]💥 Running chaos tests...[/bold red]")
    engine = ChaosEngine(Path(project_path))
    asyncio.run(engine.run_tests())


def main():
    """Main entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]ARCHON interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        logger.exception("Unhandled exception")
        raise


if __name__ == "__main__":
    main()
