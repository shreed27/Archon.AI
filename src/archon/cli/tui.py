"""
Archon TUI — A Textual-based terminal UI matching Gemini CLI exactly.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.css.query import NoMatches
from textual import events
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Footer,
    Input,
    Label,
    LoadingIndicator,
    Static,
    OptionList,
)
from textual.screen import ModalScreen
from textual.widgets.option_list import Option

from archon.cli.session_config import ExecutionMode, SessionConfig


# ─────────────────────────────────────────────────────────────────────────────
# ASCII Art (Gemini CLI Exact Match)
# ─────────────────────────────────────────────────────────────────────────────

ARCHON_LOGO = """
 [#00afff]  ███              █████╗ ██████╗  ██████╗██╗  ██╗ ██████╗ ███╗   ██╗[/]
[#5f5fff] ░░░███           ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔═══██╗████╗  ██║[/]
[#5f5fff]   ░░░███         ███████║██████╔╝██║     ███████║██║   ██║██╔██╗ ██║[/]
[#8787ff]     ░░░███       ██╔══██║██╔══██╗██║     ██╔══██║██║   ██║██║╚██╗██║[/]
[#8787ff]      ███░        ██║  ██║██║  ██║╚██████╗██║  ██║╚██████╔╝██║ ╚████║[/]
[#af87ff]    ███░          ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝[/]
[#d75f87]  ███░                                                               [/]
[#ff5f87] ░░░                                                                 [/]"""

# ─────────────────────────────────────────────────────────────────────────────
# Custom Widgets
# ─────────────────────────────────────────────────────────────────────────────


class ArchonHeader(Static):
    """The glowing, fixed header — rendered once, never redrawn."""

    DEFAULT_CSS = """
    ArchonHeader {
        width: 100%;
        height: auto;
        padding: 0 0;
        margin-bottom: 1;
    }
    #auth-info {
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    def __init__(self, project_name: str, session: SessionConfig, file_count: int) -> None:
        super().__init__()
        self.project_name = project_name
        self.session = session
        self.file_count = file_count

    def compose(self) -> ComposeResult:
        yield Static(ARCHON_LOGO, id="logo")
        yield Static(
            "[bold white]Logged in with Google:[/bold white] iamshreedshrivastava@gmail.com [dim]/auth[/dim]\n"
            "[bold white]Plan:[/bold white] Archon Code Assist for individuals",
            id="auth-info",
        )


class MessageBubble(Static):
    """A single chat message bubble — user or assistant."""

    DEFAULT_CSS = """
    MessageBubble {
        width: 100%;
        height: auto;
        margin-bottom: 1;
        padding: 0;
        layout: horizontal;
    }
    .bubble-prefix {
        width: 2;
        color: #a855f7;
    }
    .user .bubble-prefix {
        color: #94a3b8;
    }
    .bubble-content {
        width: 1fr;
    }
    """

    def __init__(self, role: str, content: str) -> None:
        super().__init__()
        self.role = role
        self.content = content
        self.add_class(role)

    def compose(self) -> ComposeResult:
        if self.role == "user":
            prefix = "> "
            color = "#f8f8f2"

            # User messages use a shaded block
            yield Static(f"[#94a3b8]> [/#94a3b8] {self.content}", classes="bubble-content")
            # Override style for user bubble
            self.styles.background = "#282a36"
            self.styles.padding = (0, 1)
        else:
            prefix = "✦ "
            yield Static(prefix, classes="bubble-prefix")
            content_widget = Static(self.content, classes="bubble-content")
            content_widget.styles.color = "#f8f8f2"
            yield content_widget


class ThinkingIndicator(Static):
    """Animated thinking indicator shown while Archon processes."""

    DEFAULT_CSS = """
    ThinkingIndicator {
        width: 100%;
        height: auto;
        padding: 0;
        display: none;
        layout: horizontal;
    }
    ThinkingIndicator.active {
        display: block;
    }
    .thinking-prefix {
        width: 2;
        color: #a855f7;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("✦ ", classes="thinking-prefix")
        yield LoadingIndicator()


class InlineModelSelector(Widget):
    """An inline model selector for switching AI models within the chat."""

    DEFAULT_CSS = """
    InlineModelSelector {
        width: 100%;
        height: auto;
        margin: 1 0;
        padding: 1 2;
        background: #282a36;
        border: solid #bd93f9;
        display: block;
    }
    #selector-title {
        color: #bd93f9;
        text-style: bold;
        margin-bottom: 1;
    }
    OptionList {
        background: transparent;
        border: none;
        height: 8;
    }
    #selector-hint {
        color: #6272a4;
        margin-top: 1;
    }
    """

    def __init__(self, options: list[dict], on_select) -> None:
        super().__init__()
        self.options = options
        self.on_select_callback = on_select

    def compose(self) -> ComposeResult:
        yield Label("Select AI Model", id="selector-title")
        option_list = OptionList(id="inline-model-options")
        for opt in self.options:
            option_list.add_option(Option(opt["name"], id=opt["id"]))
        yield option_list
        yield Label("↑ ↓ to navigate • Enter to select", id="selector-hint")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.on_select_callback(event.option.id)
        self.remove()


class FooterBlock(Container):
    """The pinned bottom block - refined and minimal."""

    DEFAULT_CSS = """
    FooterBlock {
        dock: bottom;
        height: auto;
        width: 100%;
        background: #1e1e2e;
    }
    .divider {
        content-align: center middle;
        color: #313244;
        background: transparent;
        height: 1;
        margin: 0;
    }
    #input-row {
        height: 3;
        padding: 0 2;
        background: transparent;
        layout: horizontal;
        align: left middle;
    }
    #input-prefix {
        width: 2;
        color: #fab387;
        text-style: bold;
        margin-top: 1;
    }
    #chat-input {
        width: 1fr;
        height: 3;
        border: none;
        background: transparent;
        padding: 1 0;
    }
    #chat-input:focus {
        border: none;
    }
    #status-row {
        layout: horizontal;
        height: 1;
        padding: 0 2;
        color: #cdd6f4;
        background: #181825;
    }
    #status-left {
        width: 1fr;
        color: #fab387;
    }
    #status-middle {
        width: 1fr;
        content-align: center middle;
        color: #a6adc8;
    }
    #status-right {
        width: 1fr;
        content-align: right middle;
        color: #89b4fa;
    }
    """

    def __init__(self, session: SessionConfig, project_name: str) -> None:
        super().__init__()
        self.session = session
        self.project_name = project_name

    def compose(self) -> ComposeResult:
        import shutil

        term_width = shutil.get_terminal_size().columns
        div = "─" * term_width

        yield Static(div, classes="divider")
        yield Container(
            Static("archon › ", id="input-prefix"),
            Input(
                placeholder="Type a message, /model to switch, or exit to quit",
                id="chat-input",
            ),
            id="input-row",
        )
        yield Container(
            Static(f"ready", id="status-left"),
            Static(f"{self.project_name}", id="status-middle"),
            Static("model: claude-3.5-sonnet | mode: chat", id="status-right"),
            id="status-row",
        )


class ChatHistory(ScrollableContainer):
    """Scrollable area that holds all MessageBubble widgets."""

    DEFAULT_CSS = """
    ChatHistory {
        width: 100%;
        height: 1fr;
        padding: 0 1;
        background: transparent;
        overflow-y: auto;
        overflow-x: hidden;
    }
    """


# ─────────────────────────────────────────────────────────────────────────────
# Main REPL App
# ─────────────────────────────────────────────────────────────────────────────


class ArchonApp(App):
    """
    The main Archon TUI application (Archon CLI clone).
    """

    CSS = """
    Screen {
        background: transparent;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Exit", show=True, priority=True),
        Binding("ctrl+l", "clear_history", "Clear", show=True),
    ]

    def __init__(
        self,
        project_path: Path,
        session: SessionConfig,
        manager=None,
    ) -> None:
        super().__init__()
        self.project_path = project_path
        self.session = session
        self.manager = manager
        self.initial_goal = getattr(session, "initial_goal", None)
        self._file_count = self._count_files()
        self._history: list[dict] = []
        self._pending_spec: Optional[dict] = None

    def _count_files(self) -> int:
        count = 0
        try:
            for p in self.project_path.glob("**/*"):
                if p.is_file() and not p.name.startswith("."):
                    count += 1
        except Exception:
            pass
        return count

    def compose(self) -> ComposeResult:
        yield ArchonHeader(
            project_name=self.project_path.name,
            session=self.session,
            file_count=self._file_count,
        )
        yield ChatHistory(id="chat-history")
        yield ThinkingIndicator(id="thinking")
        yield FooterBlock(session=self.session, project_name=self.project_path.name)

    def on_mount(self) -> None:
        self.query_one("#chat-input", Input).focus()

        self._add_system_message(
            "Welcome to Archon 👋\n\n"
            "Your AI software engineer.\n\n"
            "Examples:\n"
            "• create a todo app\n"
            "• build a react dashboard\n"
            "• add authentication\n"
            "• show project status\n\n"
            "Use [bold cyan]/model[/bold cyan] to switch AI models."
        )

        # Initialize status bar
        self._update_status_bar()

        if self.initial_goal:
            # Short delay to let the UI render first
            self.run_worker(self._process_initial_goal())

    def _update_status_bar(self):
        try:
            model_info = "unknown"
            if self.manager and hasattr(self.manager, "model_router"):
                model_info = self.manager.model_router.current_model

            status_right = self.query_one("#status-right", Static)
            status_right.update(f"model: {model_info} | mode: chat")
        except Exception:
            pass

    async def _process_initial_goal(self) -> None:
        await asyncio.sleep(0.5)
        if self.initial_goal == "/model":
            self._handle_slash("/model")
        else:
            self._add_message("user", self.initial_goal)
            await self._process_request(self.initial_goal)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        if text.startswith("/") or text.lower() in ("exit", "quit", "help"):
            self._handle_slash(text)
            return

        self._add_message("user", text)

        if self._pending_spec:
            self._handle_confirmation(text)
            return

        self.run_worker(self._process_request(text), exclusive=False)

    def _handle_confirmation(self, text: str) -> None:
        cmd = text.lower()
        if cmd in ("y", "yes", "go", "do it"):
            spec = self._pending_spec
            self._pending_spec = None
            self._add_system_message("\n[bold green]Proceeding with execution...[/bold green]")
            self.run_worker(self._execute_spec_in_tui(spec), exclusive=False)
        elif cmd in ("n", "no", "stop", "cancel"):
            self._pending_spec = None
            self._add_system_message("[yellow]Execution cancelled. Return to Chat.[/yellow]")
        else:
            self._add_system_message("Please answer 'y' or 'n'. Proceed with execution?")

    def _handle_slash(self, cmd: str) -> None:
        cmd_clean = cmd.strip().lower()

        if cmd_clean in ("/exit", "/quit", "exit", "quit"):
            self.exit()
            return

        if cmd_clean == "/clear":
            self.action_clear_history()
            return

        if cmd_clean == "/model":
            self._show_inline_model_selector()
            return

        if cmd_clean in ("/help", "help"):
            self._add_system_message(
                "Archon Help\n\n"
                "Available commands:\n"
                "• [bold cyan]/model[/bold cyan] - Switch AI models\n"
                "• [bold cyan]/clear[/bold cyan] - Clear chat history\n"
                "• [bold cyan]/help[/bold cyan] - Show this help message\n"
                "• [bold cyan]/exit[/bold cyan] - Exit Archon\n"
            )
            return

        # If it's not a known slash command but starts with /, treat as chat
        self._add_message("user", cmd)
        self.run_worker(self._process_request(cmd))

    def _show_inline_model_selector(self):
        if not self.manager or not hasattr(self.manager, "model_router"):
            self._add_system_message("[red]Model router not available.[/red]")
            return

        router = self.manager.model_router
        options = [
            {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
        ]

        def on_select(model_id):
            router.set_model(model_id)
            status = router.get_status()
            self._add_system_message(f"✓ {status}")
            self._update_status_bar()

        selector = InlineModelSelector(options, on_select)
        history = self.query_one("#chat-history", ChatHistory)
        history.mount(selector)
        history.scroll_end()

    async def _process_request(self, user_input: str) -> None:
        thinking = self.query_one("#thinking", ThinkingIndicator)
        thinking.add_class("active")

        try:
            await asyncio.sleep(0)

            if self.manager:
                try:
                    response = await self.manager.process_conversational_input(
                        user_input,
                        [{"role": m["role"], "content": m["content"]} for m in self._history],
                    )
                    content = response.get("message", "No response.")
                    action = response.get("action")
                    spec = response.get("spec")
                except Exception as e:
                    content = f"[red]Error:[/red] {e}"
                    action = None
                    spec = None
            else:
                await asyncio.sleep(1.2)
                content = self._demo_response(user_input)
                action = None
                spec = None

            self._add_message("assistant", content)

            if action == "select_model":
                self._pending_model_options = response.get("options")
            elif action == "execute_task" and spec:
                if self.session.mode == ExecutionMode.FAST:
                    self._add_system_message(
                        "[bold color(226)]⚡ Fast mode — executing immediately...[/bold color(226)]"
                    )
                    self.run_worker(self._execute_spec_in_tui(spec), exclusive=False)
                else:
                    self._pending_spec = spec
                    self._add_system_message("\nProceed with execution? (y/n)")

        finally:
            thinking.remove_class("active")
            self.query_one("#chat-input", Input).focus()

    async def _execute_spec_in_tui(self, spec: dict) -> None:
        thinking = self.query_one("#thinking", ThinkingIndicator)
        thinking.add_class("active")

        agent_statuses = {}
        for t in spec.get("tasks", []):
            agent = t.get("agent", "UnknownAgent")
            if agent not in agent_statuses:
                agent_statuses[agent] = "waiting"

        def get_status_text():
            lines = ["[bold]## Execution Status[/bold]"]
            for ag, st in agent_statuses.items():
                if st == "completed":
                    color = "green"
                elif st == "running":
                    color = "cyan"
                else:
                    color = "dim"
                lines.append(f"{ag.ljust(19)} → [{color}]{st}[/{color}]")
            return "\n".join(lines)

        history = self.query_one("#chat-history", ChatHistory)
        table_bubble = MessageBubble(role="assistant", content=get_status_text())
        history.mount(table_bubble)
        history.scroll_end(animate=False)

        try:
            async for update in self.manager.execute_plan(spec):
                if update["type"] == "task_started":
                    agent_statuses[update["agent"]] = "running"
                    table_bubble.query_one(".bubble-content", Static).update(get_status_text())
                elif update["type"] == "task_completed":
                    agent_statuses[update["agent"]] = "completed"
                    table_bubble.query_one(".bubble-content", Static).update(get_status_text())
                elif update["type"] == "task_failed":
                    self._add_system_message(
                        f"❌ [bold red]Task failed:[/bold red] {update['error']}"
                    )
                elif update["type"] == "deliberation_needed":
                    self._add_system_message(f"⚠️ Conflict detected: {update['conflict_type']}")
                elif update["type"] == "conflict_resolved":
                    self._add_system_message(
                        f"⚠️ [bold yellow]Conflict detected:[/bold yellow]\n"
                        f"File: {update['file']}\n"
                        f"Owned by: {update['owner']}\n"
                        f"Attempted modification by: {update['attempted']}\n"
                        f"Arbitrator evaluating versions...\n"
                        f"[bold green]✔ Selected version: {update['winner']}[/bold green]"
                    )
                elif update["type"] == "execution_summary":
                    self._add_system_message(f"[bold]Execution Summary[/bold]\n{update['summary']}")

            self._add_system_message("✨ [bold magenta]Plan execution complete![/bold magenta]")
        except Exception as e:
            self._add_system_message(f"❌ [bold red]Execution error:[/bold red] {e}")
        finally:
            thinking.remove_class("active")
            self.query_one("#chat-input", Input).focus()

    def _demo_response(self, user_input: str) -> str:
        return f"I am ready to help you with: {user_input}"

    def _add_message(self, role: str, content: str) -> None:
        self._history.append({"role": role, "content": content})
        history = self.query_one("#chat-history", ChatHistory)
        bubble = MessageBubble(role=role, content=content)
        history.mount(bubble)
        history.scroll_end(animate=False)

    def _add_system_message(self, content: str) -> None:
        self._history.append({"role": "system", "content": content})
        history = self.query_one("#chat-history", ChatHistory)
        history.mount(Static(content, classes="system-message"))
        history.scroll_end(animate=False)

    def action_clear_history(self) -> None:
        history = self.query_one("#chat-history", ChatHistory)
        for bubble in history.query("*"):
            bubble.remove()
        self._history.clear()
        self._add_system_message("History cleared.")
