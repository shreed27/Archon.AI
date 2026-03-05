"""
Terminal REPL - Claude-style streaming chat loop for Archon.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List, Dict
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.panel import Panel

from archon.manager.orchestrator import ManagerOrchestrator
from archon.cli.session_config import SessionConfig

console = Console()


class ArchonREPL:
    """
    Main REPL loop for Archon.
    Handles streaming output and conversational interaction.
    """

    def __init__(self, project_path: Path, session: SessionConfig, client: "ArchonClient"):
        self.project_path = project_path
        self.session = session
        self.client = client
        self.initial_goal = getattr(session, "initial_goal", None)
        self._pending_spec = None
        self._history: List[Dict] = []

    async def run(self):
        """Start the REPL loop."""
        self._print_welcome()

        if self.initial_goal:
            self._history.append({"role": "user", "content": self.initial_goal})
            await self._process_input(self.initial_goal)

        while True:
            try:
                user_input = await self._get_input()
                if user_input is None:
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    console.print("\n[dim]👋 Archon session terminated.[/dim]")
                    break

                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                if user_input.lower() in ["hi", "hello", "hey"]:
                    console.print("\nHi! I'm Archon.\nHow can I help you today?\n")
                    self._history.append({"role": "user", "content": user_input})
                    self._history.append(
                        {
                            "role": "assistant",
                            "content": "Hi! I'm Archon.\nHow can I help you today?",
                        }
                    )
                    continue

                self._history.append({"role": "user", "content": user_input})
                await self._process_input(user_input)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]")
            except Exception as e:
                console.print(f"\n[bold red]Error:[/bold red] {e}")

    def _print_welcome(self):
        console.print("\n[bold]Welcome to Archon 👋.[/bold]")
        console.print("How can I help you today?\n")

    async def _get_input(self) -> Optional[str]:
        """Get input from user."""
        try:
            # Using asyncio.to_thread for blocking input()
            return await asyncio.to_thread(input, "> ")
        except EOFError:
            console.print()
            return None

    async def _handle_command(self, cmd: str):
        parts = cmd.strip().split()
        base_cmd = parts[0].lower()

        if base_cmd == "/model":
            await self._model_selector()
        elif base_cmd == "/help":
            self._print_help()
        elif base_cmd == "/clear":
            console.clear()
            self._print_welcome()
        else:
            console.print(f"[red]Unknown command: {base_cmd}[/red]")

    def _print_help(self):
        console.print("\n[bold]Archon Help[/bold]")
        console.print("• [cyan]/model[/cyan] - Switch AI models")
        console.print("• [cyan]/clear[/cyan] - Clear screen")
        console.print("• [cyan]/help[/cyan] - Show this help")
        console.print("• [cyan]exit[/cyan] - Quit Archon\n")

    async def _model_selector(self):
        models = self.client.list_models()
        if not models:
            console.print("[red]Could not fetch models from server.[/red]")
            return

        console.print("\n[bold]Available models:[/bold]")
        for i, m in enumerate(models, 1):
            console.print(f"{i}. {m['name']} [dim]({m['id']})[/dim]")

        console.print("\nSelect model (number):")
        choice = (await asyncio.to_thread(input, "Select model: ")).strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                self.session.model = selected["id"]
                from .auth import save_config, get_config

                config = get_config()
                config["model"] = selected["name"]
                save_config(config)
                console.print(f"\n[green]Model set to {selected['name']}[/green]\n")
            else:
                console.print("\n[red]Invalid selection.[/red]\n")
        except ValueError:
            console.print("\n[red]Please enter a number.[/red]\n")

    async def _process_input(self, text: str):
        if self._pending_spec:
            await self._handle_confirmation(text)
            return

        from rich.spinner import Spinner
        from rich.live import Live

        full_message = ""
        action = None
        spec = None

        console.print()  # Spacer before assistant response

        # 1. Thinking phase (Intent Routing & Streaming)
        thinking_spinner = Spinner("dots", text=Text("Thinking...", style="dim"))
        with Live(thinking_spinner, console=console, transient=True):
            # We don't need a separate peek here if we use the client
            pass

        async for event in self.client.stream_chat(
            text, self.session.model, str(self.project_path)
        ):
            if event["type"] == "chunk":
                content = event["content"]
                full_message += content
                console.print(content, end="", highlight=False)
            elif event["type"] == "status":
                console.print(f"\n[dim]{event['content']}[/dim]")
            elif event["type"] == "done":
                action = event.get("action")
                spec = event.get("spec")
            elif event["type"] == "task_started":
                console.print(
                    f"🔄 [bold cyan]{event['agent'].capitalize()}Agent[/bold cyan] running: {event['description']}"
                )
            elif event["type"] == "file_created":
                console.print(f"  📝 Modified: [dim]{event['path']}[/dim]")
            elif event["type"] == "task_completed":
                console.print(
                    f"✅ [bold green]Completed[/bold green] {event['agent'].capitalize()} task."
                )
            elif event["type"] == "execution_summary":
                summary = event.get("summary", "")
                console.print(f"\n[bold green]Execution Finished![/bold green]")
                console.print(summary)
                full_message += f"\n\n{summary}"

        console.print()  # Spacer after response

        if full_message:
            self._history.append({"role": "assistant", "content": full_message})

        if action == "execute_task" and spec:
            self._pending_spec = spec
            console.print("[bold yellow]Proceed with this plan? (y/n)[/bold yellow]")

    async def _handle_confirmation(self, text: str):
        cmd = text.lower().strip()
        if cmd in ("y", "yes", "go", "do it"):
            spec = self._pending_spec
            self._pending_spec = None
            console.print("\n[bold green]Proceeding with execution...[/bold green]\n")
            await self._execute_plan(spec)
        elif cmd in ("n", "no", "stop", "cancel"):
            self._pending_spec = None
            console.print("\n[yellow]Execution cancelled.[/yellow]\n")
        else:
            console.print("[yellow]Please answer 'y' or 'n'. Proceed with execution?[/yellow]")

    async def _execute_plan(self, spec: dict):
        # In cloud mode, the plan execution is also streamed through stream_chat
        # if the user says "y".

        # For now, let's just send "proceed with the plan" to the server.
        await self._process_input("proceed with the plan")
