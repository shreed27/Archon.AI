"""
CLI command implementations.
"""

import asyncio
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt

from archon.manager.orchestrator import ManagerOrchestrator
from archon.cli.conversation import ConversationalInterface
from archon.cli.ui import ArchonUI, console
from archon.cli.session_config import SessionConfig


async def _build_session(project_path: Path) -> SessionConfig:
    """
    Run the interactive startup flow:
      1. Show header
      2. Mode picker  (Plan / Fast)
      3. Model picker
      4. Return configured SessionConfig
    """
    ArchonUI.print_header(project_path.name)

    # ── Step 1: Mode selection ────────────────────────────────────────────────
    mode = ArchonUI.show_mode_selector()

    # ── Step 2: Model selection ───────────────────────────────────────────────
    model = ArchonUI.show_model_selector()

    session = SessionConfig(
        mode=mode,
        model=model,
        project_name=project_path.name,
    )

    console.print(
        f"\n  [bold color(82)]✓[/bold color(82)] Session configured: "
        f"[bold color(226)]{session.mode_icon} {session.mode_label}[/bold color(226)]  ·  "
        f"[bold]{session.model_icon} {session.model_label}[/bold]\n"
    )

    return session


async def start_command(project_path: Path):
    """
    Start new ARCHON session with conversational interface.

    Flow:
      1. Show header
      2. Mode picker (Plan / Fast)
      3. Model picker
      4. Initialize Manager
      5. Launch REPL
    """
    # Interactive startup — mode + model selection
    session = await _build_session(project_path)

    manager = ManagerOrchestrator(str(project_path))
    await manager.initialize()

    conversation = ConversationalInterface(manager, session)
    await conversation.start_repl(project_path)


async def resume_command(project_path: Path):
    """
    Resume existing ARCHON session.
    Still prompts for mode + model since those are per-session preferences.
    """
    archon_dir = project_path / ".archon"
    if not archon_dir.exists():
        console.print("[red]No ARCHON session found. Use 'archon start'.[/red]")
        return

    # Interactive startup — mode + model selection
    session = await _build_session(project_path)

    manager = ManagerOrchestrator(str(project_path))
    await manager.load_state()

    conversation = ConversationalInterface(manager, session)
    console.print("[bold cyan]Manager:[/bold cyan] Session resumed. Ready for instructions.")
    await conversation.start_repl(project_path)


async def status_command(project_path: Path):
    """
    Show current project status.

    Displays:
    - Active tasks
    - Completed tasks
    - Agent metrics
    - File ownership map
    - Recent decisions
    """

    from rich.table import Table
    from rich.panel import Panel

    archon_dir = project_path / ".archon"

    if not archon_dir.exists():
        console.print("[red]No ARCHON session found.[/red]")
        return

    manager = ManagerOrchestrator(str(project_path))
    await manager.load_state()

    # Get status
    status = await manager.get_status()

    # Display overview
    console.print(
        Panel.fit(
            f"[bold]Project:[/bold] {status['project_name']}\n"
            f"[bold]Status:[/bold] {status['status']}\n"
            f"[bold]Tasks:[/bold] {status['tasks_completed']}/{status['tasks_total']}",
            title="ARCHON Status",
        )
    )

    # Display active tasks
    if status["active_tasks"]:
        table = Table(title="Active Tasks")
        table.add_column("Task ID", style="cyan")
        table.add_column("Agent", style="green")
        table.add_column("Model", style="yellow")
        table.add_column("Status", style="blue")

        for task in status["active_tasks"]:
            table.add_row(task["task_id"], task["agent"], task["model"], task["status"])

        console.print(table)

    # Display agent metrics
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
