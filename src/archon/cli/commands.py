"""
CLI command implementations — now backed by the Textual TUI.

Important: All setup (mode/model pickers) happens SYNCHRONOUSLY before the
Textual app starts. Textual's app.run() manages its own event loop so it
MUST NOT be called from inside an existing asyncio event loop (e.g. via
asyncio.run → async fn → app.run would nest two loops and crash).

Pattern used:
    main() [sync]
      └─ start_command() [sync]
            ├─ _build_session()    ← Rich pickers, fully sync
            └─ ArchonApp.run()    ← Textual owns the event loop from here
"""

import asyncio
from pathlib import Path
from rich.console import Console

from archon.cli.session_config import SessionConfig, ExecutionMode

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Startup setup — pickers run SYNC before TUI takes over the event loop
# ─────────────────────────────────────────────────────────────────────────────


def _print_logo() -> None:
    """Print the Archon logo once to stdout before the TUI launches."""
    from archon.cli.ui import ArchonUI

    ArchonUI.print_header()


def _build_session(project_path: Path) -> SessionConfig:
    """
    SYNCHRONOUS startup flow (bypassed interactive menus to match Gemini CLI).
    """
    return SessionConfig(
        mode=ExecutionMode.FAST,
        model="gpt-4o",  # or any default model
        project_name=project_path.name,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Commands — sync entry points called directly from main()
# ─────────────────────────────────────────────────────────────────────────────


def start_command(project_path: Path) -> None:
    """
    Start a new ARCHON session.

    SYNC function — called directly from main() NOT via asyncio.run().
    Textual's app.run() manages the event loop itself.
    """
    session = _build_session(project_path)

    if session.mode == ExecutionMode.VOICE:
        from archon.cli.voice_commands import voice_command

        asyncio.run(voice_command(project_path, voice_name=session.voice_name))
        return

    # Initialize the manager synchronously via a quick asyncio.run before TUI
    from archon.manager.orchestrator import ManagerOrchestrator

    manager = ManagerOrchestrator(str(project_path))
    asyncio.run(manager.initialize())

    # Now launch TUI — it owns the event loop from this point
    from archon.cli.tui import ArchonApp

    app = ArchonApp(project_path=project_path, session=session, manager=manager)
    app.run()  # ← Textual calls asyncio.run() itself here


def resume_command(project_path: Path) -> None:
    """Resume an existing ARCHON session."""
    archon_dir = project_path / ".archon"
    if not archon_dir.exists():
        console.print("[red]No ARCHON session found. Use 'archon start'.[/red]")
        return

    session = _build_session(project_path)

    from archon.manager.orchestrator import ManagerOrchestrator

    manager = ManagerOrchestrator(str(project_path))
    asyncio.run(manager.load_state())

    from archon.cli.tui import ArchonApp

    app = ArchonApp(project_path=project_path, session=session, manager=manager)
    app.run()


def status_command(project_path: Path) -> None:
    """
    Show current project status (non-interactive, Rich output).
    """
    from rich.table import Table
    from rich.panel import Panel
    from archon.manager.orchestrator import ManagerOrchestrator

    archon_dir = project_path / ".archon"

    if not archon_dir.exists():
        console.print("[red]No ARCHON session found.[/red]")
        return

    async def _run():
        manager = ManagerOrchestrator(str(project_path))
        await manager.load_state()
        status = await manager.get_status()

        console.print(
            Panel.fit(
                f"[bold]Project:[/bold] {status['project_name']}\n"
                f"[bold]Status:[/bold]  {status['status']}\n"
                f"[bold]Tasks:[/bold]   {status['tasks_completed']}/{status['tasks_total']}",
                title="ARCHON Status",
            )
        )

        if status["active_tasks"]:
            table = Table(title="Active Tasks")
            table.add_column("Task ID", style="cyan")
            table.add_column("Agent", style="green")
            table.add_column("Model", style="yellow")
            table.add_column("Status", style="blue")
            for task in status["active_tasks"]:
                table.add_row(task["task_id"], task["agent"], task["model"], task["status"])
            console.print(table)

        if status["agent_metrics"]:
            table = Table(title="Agent Performance")
            table.add_column("Agent", style="cyan")
            table.add_column("Tasks", style="green")
            table.add_column("Avg Quality", style="yellow")
            table.add_column("Success Rate", style="blue")
            for agent, metrics in status["agent_metrics"].items():
                table.add_row(
                    agent,
                    str(metrics["tasks_completed"]),
                    f"{metrics['avg_quality']:.2f}",
                    f"{metrics['success_rate']:.1%}",
                )
            console.print(table)

    asyncio.run(_run())
