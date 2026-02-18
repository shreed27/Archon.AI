"""
Conversational interface for ARCHON.

Handles natural language interaction between user and Manager.
"""

from typing import TYPE_CHECKING, Optional
from rich.console import Console
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from archon.manager.orchestrator import ManagerOrchestrator

from archon.cli.session_config import SessionConfig, ExecutionMode

console = Console()


class ConversationalInterface:
    """
    Natural language interface for ARCHON.

    Responsibilities:
    - Parse user input
    - Display Manager responses
    - Show progress updates
    - Handle multi-turn conversations
    - Respect session mode (plan vs fast) and model override
    """

    def __init__(self, manager: "ManagerOrchestrator", session: SessionConfig):
        self.manager = manager
        self.session = session
        self.conversation_history = []

    async def process_goal(self, goal: str):
        """
        Process initial user goal.

        In PLAN mode:
          1. Manager parses goal → specification
          2. Shows plan to user
          3. User approves / modifies / cancels
          4. Execute on approval

        In FAST mode:
          1. Manager parses goal → specification
          2. Execute immediately (no confirmation step)
        """

        self.conversation_history.append({"role": "user", "content": goal})

        # Show thinking spinner
        with Live(Spinner("dots", text="Manager analyzing goal..."), console=console):
            spec = await self.manager.parse_goal_to_spec(goal)

        # Show specification
        console.print("\n[bold cyan]Manager:[/bold cyan]")
        console.print(f"I understand. Here's my plan:\n")
        console.print(f"[bold]Goal:[/bold] {spec['goal']}")
        console.print(f"[bold]Components:[/bold]")
        for component in spec["components"]:
            console.print(f"  • {component}")

        console.print(f"\n[bold]Task Breakdown:[/bold]")
        for task in spec["tasks"]:
            console.print(f"  {task['id']}: {task['description']} → {task['agent']}")

        # ── Mode-dependent confirmation ──────────────────────────────────────
        if self.session.mode == ExecutionMode.FAST:
            console.print(
                f"\n[bold color(226)]⚡ Fast mode — executing immediately...[/bold color(226)]"
            )
            await self._execute_plan(spec)

        else:  # PLAN mode
            proceed = Prompt.ask(
                "\n[bold green]Proceed with this plan?[/bold green]",
                choices=["yes", "no", "modify"],
                default="yes",
            )

            if proceed == "yes":
                await self._execute_plan(spec)
            elif proceed == "modify":
                modification = Prompt.ask("[bold green]What would you like to change?[/bold green]")
                await self.process_input(modification)
            else:
                console.print("[yellow]Plan cancelled.[/yellow]")

    async def _execute_plan(self, spec: dict):
        """
        Execute the plan with live progress updates.
        """

        console.print("\n[bold green]🚀 Executing plan...[/bold green]\n")

        # Execute with progress tracking
        async for update in self.manager.execute_plan(spec):
            if update["type"] == "task_started":
                console.print(f"[cyan]→[/cyan] {update['agent']} starting: {update['description']}")
            elif update["type"] == "task_completed":
                console.print(
                    f"[green]✓[/green] {update['agent']} completed: {update['description']}"
                )
            elif update["type"] == "deliberation_needed":
                console.print(f"[yellow]⚠[/yellow] Conflict detected: {update['conflict_type']}")
                await self._handle_deliberation(update["conflict"])
            elif update["type"] == "tool_execution":
                console.print(f"[blue]🔧[/blue] Using external tool: {update['tool_name']}")
            elif update["type"] == "quality_gate_failed":
                console.print(f"[red]✗[/red] Quality gate failed: {update['reason']}")

        console.print("\n[bold green]✅ Plan execution complete![/bold green]")

    async def _handle_deliberation(self, conflict: dict):
        """
        Handle agent deliberation by showing proposals and decision.
        """

        console.print("\n[bold yellow]Deliberation Required[/bold yellow]")
        console.print(f"Conflict: {conflict['conflict_type']}\n")

        console.print("[bold]Proposals:[/bold]")
        for proposal in conflict["proposals"]:
            console.print(f"\n[cyan]{proposal['agent']}:[/cyan]")
            console.print(f"  Proposal: {proposal['proposal']}")
            console.print(f"  Reasoning: {proposal['reasoning']}")
            console.print(f"  Risk: {proposal['risk_score']:.1%}")

        # Manager decides
        with Live(Spinner("dots", text="Manager evaluating..."), console=console):
            decision = await self.manager.arbitrator.resolve_conflict(conflict)

        console.print(f"\n[bold green]Manager Decision:[/bold green]")
        console.print(f"Chosen: {decision['chosen_proposal']}")
        console.print(f"Reasoning: {decision['reasoning']}\n")

    async def process_input(self, user_input: str):
        """
        Process general user input during conversation.
        """

        self.conversation_history.append({"role": "user", "content": user_input})

        # Manager processes input
        response = await self.manager.process_conversational_input(
            user_input, self.conversation_history
        )

        console.print(f"\n[bold cyan]Manager:[/bold cyan]")
        console.print(response["message"])

        if response.get("action"):
            await self._execute_action(response["action"])

    # ─────────────────────────────────────────────────────────────────────────
    # Slash commands
    # ─────────────────────────────────────────────────────────────────────────

    async def _handle_slash_command(self, cmd: str) -> bool:
        """
        Handle /slash commands. Returns True if handled, False otherwise.
        """
        cmd = cmd.strip().lower()

        if cmd in ["/exit", "/quit", "exit", "quit"]:
            return False  # Signal to exit REPL

        if cmd == "/help":
            console.print(
                Panel(
                    "  [bold color(39)]/mode[/bold color(39)]    — Switch execution mode (Plan / Fast)\n"
                    "  [bold color(201)]/model[/bold color(201)]   — Switch AI model\n"
                    "  [bold white]/status[/bold white]  — Show project status\n"
                    "  [bold white]/exit[/bold white]    — Quit ARCHON",
                    title="[bold]Available Commands[/bold]",
                    border_style="color(39)",
                )
            )
            Prompt.ask("Press Enter to continue")
            return True

        if cmd == "/mode":
            from archon.cli.ui import ArchonUI

            new_mode = ArchonUI.show_mode_selector()
            self.session.mode = new_mode
            console.print(
                f"[bold color(82)]✓[/bold color(82)] Mode updated to "
                f"[bold color(226)]{self.session.mode_icon} {self.session.mode_label}[/bold color(226)]"
            )
            Prompt.ask("Press Enter to continue")
            return True

        if cmd == "/model":
            from archon.cli.ui import ArchonUI

            new_model = ArchonUI.show_model_selector()
            self.session.model = new_model
            console.print(
                f"[bold color(82)]✓[/bold color(82)] Model updated to "
                f"[bold]{self.session.model_icon} {self.session.model_label}[/bold]"
            )
            Prompt.ask("Press Enter to continue")
            return True

        if cmd == "/status":
            await self._show_status()
            Prompt.ask("Press Enter to continue")
            return True

        return True  # Unknown slash command — just continue

    async def _show_status(self):
        """Display current session status."""
        from archon.cli.session_config import MODE_METADATA

        mode_meta = MODE_METADATA[self.session.mode]

        table = Table(title="Session Status", box=None, show_header=False)
        table.add_column("Key", style="bold color(39)", width=16)
        table.add_column("Value", style="white")

        table.add_row("Mode", f"{mode_meta['icon']} {mode_meta['label']}")
        table.add_row("Model", f"{self.session.model_icon} {self.session.model_label}")
        table.add_row("Provider", self.session.model_provider)
        table.add_row("Project", self.session.project_name)

        console.print(table)

    # ─────────────────────────────────────────────────────────────────────────
    # Main REPL
    # ─────────────────────────────────────────────────────────────────────────

    async def start_repl(self, project_path):
        """
        Starts the main Read-Eval-Print Loop (REPL).
        """
        import readline  # Fixes arrow keys and history
        from archon.cli.ui import ArchonUI

        while True:
            # Refresh UI for next turn
            console.clear()
            ArchonUI.print_header(project_path.name)

            # Count files
            file_count = ArchonUI.get_file_count(project_path)

            # Render the UI Layout — now passes mode + model from session
            ArchonUI.render_input_look(
                project_path,
                model_name=self.session.model_label,
                file_count=file_count,
                mode=self.session.mode_label,
                mode_icon=self.session.mode_icon,
            )

            # Robust Input Prompt
            try:
                user_input = Prompt.ask(" [bold white]>[/bold white]")
            except KeyboardInterrupt:
                break

            console.print("")  # Separator for response

            if not user_input.strip():
                continue

            # Handle slash commands first
            if user_input.startswith("/") or user_input.lower() in ["exit", "quit"]:
                should_continue = await self._handle_slash_command(user_input)
                if not should_continue:
                    break
                continue

            # Process user request
            await self._handle_user_request(user_input)

    async def _handle_user_request(self, user_input: str):
        """
        Simulated Manager response logic.
        Respects session mode (plan vs fast) and model override.
        """
        import asyncio

        c = Console()

        # 1. Thinking Animation
        with Live(
            Spinner(
                "dots",
                text="[bold green]Manager analyzing request...[/bold green]",
                style="bold green",
            ),
            console=c,
            transient=True,
        ):
            await asyncio.sleep(1.5)  # Simulate thinking

        # 2. Display Manager's Decision
        plan_panel = None

        if "todo" in user_input.lower() or "app" in user_input.lower():
            grid = Table.grid(expand=True)
            grid.add_column()
            grid.add_row("[bold cyan]AGENTS SELECTED:[/bold cyan]")
            grid.add_row("  • [bold magenta]Architect[/bold magenta] (Structure & Design)")
            grid.add_row("  • [bold blue]Frontend Dev[/bold blue] (React/Next.js)")
            grid.add_row("  • [bold yellow]Backend Dev[/bold yellow] (API/Database)")
            grid.add_row("")
            grid.add_row("[bold cyan]GENERATED TASKS:[/bold cyan]")
            grid.add_row("  1. [white]Initialize Next.js Project[/white]")
            grid.add_row("  2. [white]Design Schema (SQLite)[/white]")
            grid.add_row("  3. [white]Implement API Routes[/white]")
            grid.add_row("  4. [white]Build Frontend Components[/white]")

            # Show mode indicator in plan
            mode_note = (
                f"\n[dim]Mode: {self.session.mode_icon} {self.session.mode_label}  ·  "
                f"Model: {self.session.model_icon} {self.session.model_label}[/dim]"
            )
            grid.add_row(mode_note)

            plan_panel = Panel(
                grid,
                title="[bold green]MANAGER PLAN[/bold green]",
                border_style="bold green",
                subtitle="[dim]4 Tasks • 3 Agents[/dim]",
            )
        else:
            plan_panel = Panel(
                f"[white]I have analyzed your request: '{user_input}'[/white]\n\n"
                "[bold cyan]Action:[/bold cyan] Awaiting further specification.\n"
                "[bold cyan]Status:[/bold cyan] Ready to execute custom logic.\n"
                f"[dim]Mode: {self.session.mode_icon} {self.session.mode_label}  ·  "
                f"Model: {self.session.model_icon} {self.session.model_label}[/dim]",
                title="[bold green]SYSTEM ACKNOWLEDGED[/bold green]",
                border_style="bold green",
            )

        c.print(plan_panel)
        c.print("")

        # In FAST mode — skip confirmation prompt
        if self.session.mode == ExecutionMode.FAST:
            c.print(
                "[bold color(226)]⚡ Fast mode — proceeding without confirmation.[/bold color(226)]"
            )
            c.print("")
        else:
            # PLAN mode — user reviews before continuing
            Prompt.ask("[dim]Review plan above. Press Enter to continue...[/dim]")

    async def _execute_action(self, action: dict):
        """Execute action determined by Manager."""

        if action["type"] == "execute_task":
            await self._execute_plan(action["spec"])
        elif action["type"] == "show_status":
            await self._show_status()
        elif action["type"] == "modify_architecture":
            pass
        elif action.get("message"):
            pass
