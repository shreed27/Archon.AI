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
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Footer,
    Input,
    Label,
    LoadingIndicator,
    Static,
)

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
            color = "#f8f8f2"
            yield Static(prefix, classes="bubble-prefix")
            yield Static(f"[{color}]{self.content}[/{color}]", classes="bubble-content")


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


class FooterBlock(Container):
    """The pinned bottom block from Archon CLI."""

    DEFAULT_CSS = """
    FooterBlock {
        dock: bottom;
        height: auto;
        width: 100%;
    }
    .divider {
        content-align: center middle;
        color: #44475a;
        background: transparent;
        height: 1;
    }
    #shortcuts-hint {
        content-align: right middle;
        color: #6272a4;
        height: 1;
        padding: 0 1;
    }
    #skills-row {
        layout: horizontal;
        height: 1;
        padding: 0 1;
        background: #282a36;
    }
    #skills-left {
        width: 1fr;
        color: #6272a4;
    }
    #skills-right {
        width: auto;
        color: #6272a4;
    }
    #input-row {
        height: 1;
        padding: 0 1;
        background: #282a36;
        layout: horizontal;
    }
    #input-prefix {
        width: 2;
        color: #bd93f9;
        text-style: bold;
    }
    #chat-input {
        width: 1fr;
        height: 1;
        border: none;
        background: transparent;
        padding: 0;
    }
    #chat-input:focus {
        border: none;
    }
    #status-row {
        layout: horizontal;
        height: 1;
        padding: 0 1;
        color: #f8f8f2;
    }
    #status-left {
        width: 1fr;
    }
    #status-middle {
        width: 1fr;
        content-align: center middle;
        color: #ff5555;
    }
    #status-right {
        width: auto;
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

        yield Static("? for shortcuts", id="shortcuts-hint")
        yield Static(div, classes="divider")

        yield Container(
            Static("shift+tab to accept edits", id="skills-left"),
            Static("1 ARCHON.md file | 84 skills", id="skills-right"),
            id="skills-row",
        )
        yield Static(div, classes="divider")

        yield Container(
            Static(">", id="input-prefix"),
            Input(
                placeholder="  Type your message or @path/to/file",
                id="chat-input",
            ),
            id="input-row",
        )
        yield Static(div, classes="divider")

        yield Container(
            Static(f"~/{self.project_name} [dim](main*)[/dim]", id="status-left"),
            Static("no sandbox", id="status-middle"),
            Static("[dim]/model[/dim] Auto (Archon Manager)", id="status-right"),
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
        self._file_count = self._count_files()
        self._history: list[dict] = []

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
            "[bold white]i[/bold white] Update successful! The new version will be used on your next run.\n"
            "✦ I am Archon CLI, your interactive software engineering assistant. I can help you with:\n\n"
            "  * [bold white]Codebase Investigation:[/bold white] Mapping architecture and diagnosing complex bugs using\n"
            "    [#af87ff]codebase_investigator[/].\n"
            "  * [bold white]Feature Implementation:[/bold white] Taking tasks from research and strategy through to verified\n"
            "    execution.\n"
            "  * [bold white]Application Prototyping:[/bold white] Building functional, modern prototypes (Web, API, CLI, Mobile,\n"
            "    Games).\n"
            "  * [bold white]Specialized Tasks:[/bold white] Activating expert skills for things like AWS/Azure/Terraform diagrams,\n"
            "    security audits, performance optimization, and more.\n"
            "  * [bold white]System Help:[/bold white] Explaining CLI features and configuration via [#af87ff]cli_help[/].\n\n"
            "How can I help you with your project today?\n"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        if text.startswith("/") or text.lower() in ("exit", "quit"):
            self._handle_slash(text.lower())
            return

        self._add_message("user", text)
        self.run_worker(self._process_request(text), exclusive=False)

    def _handle_slash(self, cmd: str) -> None:
        cmd = cmd.strip()

        if cmd in ("/exit", "/quit", "exit", "quit"):
            self.exit()
            return

        if cmd == "/clear":
            self.action_clear_history()
            return

        self._add_system_message(
            f"Unknown command: [bold]{cmd}[/bold]  — Try [bold]? for shortcuts[/bold]"
        )

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
                except Exception as e:
                    content = f"[red]Error:[/red] {e}"
            else:
                await asyncio.sleep(1.2)
                content = self._demo_response(user_input)

            self._add_message("assistant", content)

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
