"""
Rich UI components for ARCHON CLI.
"""

import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich import box
from rich.style import Style

console = Console()


class ArchonUI:
    """
    Handles the visual presentation of the ARCHON CLI.
    """

    @staticmethod
    def get_file_count(path: Path) -> int:
        """Recursively counts files in the project."""
        count = 0
        try:
            for _ in path.glob("**/*"):
                if _.is_file() and not _.name.startswith("."):
                    count += 1
        except Exception:
            return 0
        return count

    @staticmethod
    def print_header(project_name: str = "Unknown"):
        """Prints the Cyberpunk / Web3 style header."""

        # 1. The Glitch/Cyberpunk Header
        archon_art = """
    █████╗ ██████╗  ██████╗██╗  ██╗ ██████╗ ███╗   ██╗
   ██╔══██╗██╔══██╗██╔════╝██║  ██║██╔═══██╗████╗  ██║
   ███████║██████╔╝██║     ███████║██║   ██║██╔██╗ ██║
   ██╔══██║██╔══██╗██║     ██╔══██║██║   ██║██║╚██╗██║
   ██║  ██║██║  ██║╚██████╗██║  ██║╚██████╔╝██║ ╚████║
   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""
        # Neon Gradient: Electric Blue -> Neon Pink
        styled_art = Text(archon_art)
        styled_art.stylize("bold color(39)", 0, 70)  # Cyan
        styled_art.stylize("bold color(63)", 70, 140)  # Blue
        styled_art.stylize("bold color(201)", 140, 210)  # Magenta

        # Frame the header
        header_panel = Panel(
            Align.center(styled_art),
            box=box.HEAVY,
            border_style="color(39)",
            title="[bold italic color(82)] SYSTEM::ONLINE [/bold italic color(82)]",
            subtitle="[bold color(226)] v0.1.0-ALPHA // NEURAL LINK ESTABLISHED [/bold color(226)]",
            padding=(1, 2),
        )
        console.print(header_panel)

        # 2. Viral Capabilities Grid
        # 3 Columns: Build, Refactor, Ship
        status_table = Table(show_header=False, show_edge=False, box=None, expand=True)
        status_table.add_column("1", ratio=1, justify="center")
        status_table.add_column("2", ratio=1, justify="center")
        status_table.add_column("3", ratio=1, justify="center")

        status_table.add_row(
            Panel(
                "[bold white] 🦞 BUILD FULL-STACK[/bold white]",
                box=box.ROUNDED,
                style="color(235)",
            ),
            Panel(
                "[bold white] 🦞 AGI REFACTORING[/bold white]",
                box=box.ROUNDED,
                style="color(235)",
            ),
            Panel(
                "[bold white] 🦞 SHIP TO PROD[/bold white]",
                box=box.ROUNDED,
                style="color(235)",
            ),
        )
        console.print(status_table)
        console.print("")

    @staticmethod
    def render_input_look(
        project_path: Path, model_name: str = "Auto (Gemini 2.5)", file_count: int = 0
    ):
        """
        Renders the cracked design input context.
        """
        # Context Line with "Hacker" aesthetic
        console.print(
            Text.assemble(
                (" >_ MAPPED: ", "bold color(82)"),
                (f"{file_count} FILES ", "bold white"),
                (" :: ", "dim white"),
                (" CONTEXT: ", "bold color(82)"),
                (" ARCHON.md ", "bold white"),
                (" [LOCKED]", "bold red"),
            )
        )

        # Cyberpunk Input Box
        # We use a Heavy box with a Neon border
        console.print(
            Panel(
                Text(" " * 60, style="dim white"),  # Empty space for input area height
                box=box.HEAVY,
                border_style="bold white",  # White Border
                title="[bold color(39)] ⌨️  NEURAL INPUT [/bold color(39)]",
                title_align="left",
                subtitle="[bold color(226)] EXECUTE [/bold color(226)]",
                subtitle_align="right",
                expand=True,
            )
        )

        # Footer Bar - Clean & Minimal
        footer_table = Table.grid(expand=True)
        footer_table.add_column(justify="left", ratio=1)
        footer_table.add_column(justify="center", ratio=1)  # Restore centered Sandbox status
        footer_table.add_column(justify="right", ratio=1)

        # Path formatting
        try:
            rel_path = f"~/{project_path.relative_to(Path.home())}"
        except ValueError:
            rel_path = str(project_path)

        footer_table.add_row(
            Text(f" 📂 {rel_path} ", style="bold white"),  # White Text
            Text(" no sandbox ", style="bold white"),  # White Text
            Text(f" 🤖 {model_name} ", style="bold white"),  # White Text
        )

        console.print(footer_table)

    @staticmethod
    def render_scrolling_prompt(project_path: Path, file_count: int = 0):
        """
        Renders a minimal scrolling prompt.
        """
        # Context Line
        # [MAPPED: 58] [CONTEXT: ARCHON.md]
        # >_

        console.print(
            Text.assemble(
                ("\n[", "bold white"),
                (f"MAPPED:{file_count}", "bold white"),  # White
                ("] ", "bold white"),
                ("[", "bold white"),
                (f"CONTEXT: {project_path.name}", "bold white"),  # White
                ("] ", "bold white"),
            )
        )
        console.print(Text(" >_ ", style="bold white"), end="")
