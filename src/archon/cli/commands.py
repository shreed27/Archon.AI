"""
CLI command implementations — now backed by a terminal REPL loop.

Pattern used:
    main() [sync]
      └─ start_command() [sync]
            ├─ _build_session()    ← fully sync
            └─ ArchonREPL.run()    ← REPL loop
"""

import asyncio
from pathlib import Path
from typing import Optional
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


def _build_session(project_path: Path, initial_goal: Optional[str] = None) -> SessionConfig:
    """
    SYNCHRONOUS startup flow (bypassed interactive menus to match Gemini CLI).
    """
    return SessionConfig(
        mode=ExecutionMode.FAST,
        model="gpt-4o",  # or any default model
        project_name=project_path.name,
        initial_goal=initial_goal,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Commands — sync entry points called directly from main()
# ─────────────────────────────────────────────────────────────────────────────


def start_command(project_path: Path, initial_goal: Optional[str] = None) -> None:
    """
    Start a new ARCHON session.
    """
    from archon.cli.auth import get_session, login, get_config

    session_data = get_session()
    if not session_data:
        token = login()
        if not token:
            return

    config = get_config()
    session = SessionConfig(
        mode=ExecutionMode.FAST,
        model=config.get("model", "Claude 3.5 Sonnet"),
        project_name=project_path.name,
        initial_goal=initial_goal,
    )

    # Use ArchonClient instead of direct ManagerOrchestrator
    from archon.cli.client import ArchonClient

    client = ArchonClient()

    # Launch Terminal REPL
    from archon.cli.repl import ArchonREPL

    repl = ArchonREPL(project_path=project_path, session=session, client=client)
    asyncio.run(repl.run())


def resume_command(project_path: Path) -> None:
    """Resume an existing ARCHON session."""
    # Similar to start_command in cloud mode
    start_command(project_path)


def add_command(project_path: Path, feature_description: str) -> None:
    """Implement feature addition bypassing TUI."""
    archon_dir = project_path / ".archon"
    if not archon_dir.exists():
        console.print("[red]No ARCHON session found. Initialize first with 'archon start'.[/red]")
        return

    from archon.manager.orchestrator import ManagerOrchestrator

    manager = ManagerOrchestrator(str(project_path))

    async def run_feature():
        await manager.load_state()
        console.print(f"[bold cyan]Planning feature: {feature_description}[/bold cyan]")

        spec = await manager.plan_feature(feature_description)

        console.print("\n[bold]Feature Execution Plan[/bold]")
        console.print(manager.format_plan_summary(spec))
        console.print()

        async for event in manager.execute_feature_plan(spec):
            if event["type"] == "task_started":
                console.print(f"🔄 Starting [{event['agent']}]: {event['description']}")
            elif event["type"] == "file_created":
                console.print(f"📝 Modified file: {event['path']}")
            elif event["type"] == "conflict_resolved":
                console.print(f"⚠️ Conflict resolved in {event['file']} - winner: {event['winner']}")
            elif event["type"] == "task_completed":
                console.print(f"✅ Completed [{event['agent']}]: {event['description']}")
            elif event["type"] == "task_failed":
                console.print(f"❌ Failed: {event['error']}")
            elif event["type"] == "execution_summary":
                console.print("\n" + event["summary"])

    asyncio.run(run_feature())


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
