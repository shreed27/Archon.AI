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
from rich.rule import Rule
from rich.columns import Columns

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
    def print_header(project_name: str = "Archon.AI"):
        """Prints the minimal Gemini CLI style header."""

        archon_art = """▝▜▄  
  ▝▜▄
 ▗▟▀ 
▝▀    """

        console.print(
            Text.assemble(
                (archon_art, "bold color(39)"),
                (" Archon CLI", "bold white"),
                (" v0.1.0-ALPHA", "dim white"),
            )
        )
        console.print("")

    @staticmethod
    def render_input_look(
        project_path: Path,
        model_name: str = "Auto (Manager decides)",
        file_count: int = 0,
        mode: str = "Plan",
        mode_icon: str = "📋",
    ):
        """
        Renders the cracked design input context.
        Now shows mode and model in the status bar.
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

        # Cyberpunk Input Separator
        console.rule("[bold color(39)] NEURAL INPUT [/bold color(39)]", style="bold white")

        # Status Line — now shows Mode + Model
        status_text = Text.assemble(
            (f" 📂 {project_path.name} ", "bold color(39)"),
            (" :: ", "dim white"),
            (f" {mode_icon} {mode} ", "bold color(226)"),
            (" :: ", "dim white"),
            (f" 🤖 {model_name} ", "bold white"),
        )

        console.print(status_text, justify="right")
        console.print("")  # Spacing for prompt

    # ─────────────────────────────────────────────────────────────────────────
    # Mode Selector
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def show_mode_selector() -> "ExecutionMode":
        """
        Interactive mode picker rendered in the terminal.
        Returns the chosen ExecutionMode.

        Displays:
          ┌─ Conversation mode ──────────────────────────────┐
          │  [1] 📋 Planning                                  │
          │      Agent can plan before executing tasks.       │
          │      Use for deep research, complex tasks...      │
          │                                                   │
          │  [2] ⚡ Fast                                      │
          │      Agent will execute tasks directly.           │
          │      Use for simple tasks that can be done faster │
          └───────────────────────────────────────────────────┘
        """
        from archon.cli.session_config import ExecutionMode, MODE_METADATA

        console.print("")
        console.rule("[bold color(39)] CONVERSATION MODE [/bold color(39)]", style="color(39)")
        console.print("")

        options = list(ExecutionMode)

        for i, mode in enumerate(options, 1):
            meta = MODE_METADATA[mode]
            color = meta["color"]

            # Highlighted option block
            label_text = Text.assemble(
                (f"  [{i}]  ", "bold white"),
                (f"{meta['icon']} {meta['label']}", f"bold {color}"),
            )
            detail_text = Text.assemble(
                ("       ", ""),
                (meta["tagline"], "white"),
                ("\n       ", ""),
                (meta["detail"], "dim white"),
            )

            console.print(label_text)
            console.print(detail_text)
            console.print("")

        while True:
            try:
                raw = console.input(
                    "[bold color(39)] ❯ Select mode [1/2]: [/bold color(39)]"
                ).strip()
                idx = int(raw) - 1
                if 0 <= idx < len(options):
                    chosen = options[idx]
                    meta = MODE_METADATA[chosen]
                    console.print(
                        f"\n  [bold color(82)]✓[/bold color(82)] Mode set to "
                        f"[bold {meta['color']}]{meta['icon']} {meta['label']}[/bold {meta['color']}]\n"
                    )
                    return chosen
                else:
                    console.print(f"  [red]Enter 1 or 2.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print(f"  [red]Enter 1 or 2.[/red]")

    # ─────────────────────────────────────────────────────────────────────────
    # Model Selector
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def show_model_selector() -> str:
        """
        Interactive model picker rendered in the terminal.
        Returns the chosen model ID string.

        Groups models by provider, shows icon + label + tier badge.
        """
        from archon.cli.session_config import MODEL_METADATA, MODEL_PICKER_ORDER

        console.print("")
        console.rule("[bold color(201)] MODEL SELECTION [/bold color(201)]", style="color(201)")
        console.print("")

        # Build ordered list, filtering to only known models
        ordered = [m for m in MODEL_PICKER_ORDER if m in MODEL_METADATA]

        # Group by provider for display
        provider_colors = {
            "Archon": "color(82)",
            "Google": "color(39)",
            "Anthropic": "color(208)",
            "OpenAI": "color(46)",
            "OSS": "color(245)",
        }

        tier_badges = {
            "auto": "[dim]AUTO[/dim]",
            "premium": "[bold color(226)]PREMIUM[/bold color(226)]",
            "standard": "[dim white]STD[/dim white]",
            "fast": "[bold color(82)]FAST[/bold color(82)]",
        }

        current_provider = None
        index_map = {}  # display_number -> model_id

        display_num = 1
        for model_id in ordered:
            meta = MODEL_METADATA[model_id]
            provider = meta["provider"]
            color = provider_colors.get(provider, "white")

            # Print provider header when it changes
            if provider != current_provider:
                if current_provider is not None:
                    console.print("")
                console.print(f"  [bold {color}]── {provider} ──[/bold {color}]")
                current_provider = provider

            tier = meta.get("tier", "standard")
            badge = tier_badges.get(tier, "")

            label_text = Text.assemble(
                (f"  [{display_num:>2}]  ", "bold white"),
                (f"{meta['icon']} ", ""),
                (meta["label"], f"bold {color}"),
                ("  ", ""),
            )
            console.print(label_text, end="")
            console.print(badge)

            index_map[display_num] = model_id
            display_num += 1

        console.print("")

        while True:
            try:
                raw = console.input(
                    f"[bold color(201)] ❯ Select model [1-{len(index_map)}]: [/bold color(201)]"
                ).strip()
                idx = int(raw)
                if idx in index_map:
                    chosen_id = index_map[idx]
                    meta = MODEL_METADATA[chosen_id]
                    provider = meta["provider"]
                    color = provider_colors.get(provider, "white")
                    console.print(
                        f"\n  [bold color(82)]✓[/bold color(82)] Model set to "
                        f"[bold {color}]{meta['icon']} {meta['label']}[/bold {color}]\n"
                    )
                    return chosen_id
                else:
                    console.print(f"  [red]Enter a number between 1 and {len(index_map)}.[/red]")
            except (ValueError, KeyboardInterrupt):
                console.print(f"  [red]Enter a number between 1 and {len(index_map)}.[/red]")

    @staticmethod
    def render_scrolling_prompt(project_path: Path, file_count: int = 0):
        """
        Renders a minimal scrolling prompt.
        """
        console.print(
            Text.assemble(
                ("\n[", "bold white"),
                (f"MAPPED:{file_count}", "bold white"),
                ("] ", "bold white"),
                ("[", "bold white"),
                (f"CONTEXT: {project_path.name}", "bold white"),
                ("] ", "bold white"),
            )
        )
        console.print(Text(" >_ ", style="bold white"), end="")
