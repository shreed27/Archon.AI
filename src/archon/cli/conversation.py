"""
Conversational interface for ARCHON.

Handles natural language interaction between user and Manager.
"""

from typing import TYPE_CHECKING
from rich.console import Console
from rich.prompt import Prompt
from rich.live import Live
from rich.spinner import Spinner

if TYPE_CHECKING:
    from archon.manager.orchestrator import ManagerOrchestrator

console = Console()


class ConversationalInterface:
    """
    Natural language interface for ARCHON.

    Responsibilities:
    - Parse user input
    - Display Manager responses
    - Show progress updates
    - Handle multi-turn conversations
    """

    def __init__(self, manager: "ManagerOrchestrator"):
        self.manager = manager
        self.conversation_history = []

    async def process_goal(self, goal: str):
        """
        Process initial user goal.

        Flow:
        1. Manager parses goal into specification
        2. Manager creates task DAG
        3. Manager shows plan
        4. User confirms
        5. Manager executes
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

        # Ask for confirmation
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

            # Render the UI Layout
            ArchonUI.render_input_look(project_path, "Auto (Gemini 2.5)", file_count)

            # Move cursor UP to the input box
            # 1 line for Footer
            # 1 line for Panel Bottom Border
            # 1 line for Panel Padding/Content (approx)
            # We want to be inside the box.
            # \033[3A moves up 3 lines.

            # Position cursor for input
            print("\033[3A", end="", flush=True)
            # Move right to align with "> " inside the box (if we printed it)
            # ArchonUI prints: "> Type your message..." inside the panel.
            # We want to overwrite that or type next to it?
            # User wants to "type in message box".
            # We'll just print a prompt effectively overwriting the placeholder text line.

            console.print("  > ", end="")  # Indent inside box

            try:
                user_input = input("")  # Use standard input to keep it simple with cursor
            except KeyboardInterrupt:
                break

            # Move cursor back down below the footer to print response
            print("\033[3B", end="", flush=True)
            console.print("")  # Newline

            if not user_input.strip():
                continue

            if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                break

            if user_input.lower() == "/help":
                console.print(
                    Panel(
                        "• /exit - Quit\n• /status - Project Status\n• @file - Context",
                        title="Help",
                    )
                )
                # Pause to let user read
                Prompt.ask("Press Enter to continue")
                continue

            # Process input (Standard "Coming Soon" with Rizz)
            await self._respond_with_rizz()

    async def _respond_with_rizz(self):
        """Standard placeholder response."""
        from rich.console import Console
        from rich.panel import Panel

        c = Console()
        c.print("")
        c.print(
            Panel(
                "[bold color(201)]Yo, hold up! 🛑[/bold color(201)]\n\nI'm still in the lab getting my neural pathways aligned.\nThis feature is [bold cyan]coming soon[/bold cyan] to take your project to a production-level masterpiece.\n\n[italic]Stay tuned! 🚀✨[/italic]",
                title="Construction Zone",
                border_style="color(63)",
            )
        )
        c.print("")
        # Pause so they can read it before the loop clears the screen
        Prompt.ask("[dim]Press Enter to continue...[/dim]")

    async def _execute_action(self, action: dict):
        """Execute action determined by Manager."""

        if action["type"] == "execute_task":
            await self._execute_plan(action["spec"])
        elif action["type"] == "show_status":
            status = await self.manager.get_status()
            # Display status (similar to status_command)
        elif action["type"] == "modify_architecture":
            # Handle architecture modifications
            pass
        elif action.get("message"):
            # Just a fallback if only message is present
            pass
