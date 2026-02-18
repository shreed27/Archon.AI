"""
Session configuration for an ARCHON CLI session.

Holds user-selected mode and model that persist across the REPL loop.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ExecutionMode(str, Enum):
    """
    Execution mode controls how the Manager handles tasks.

    PLAN  — Manager builds a full plan and shows it to the user for review/edit
            before any implementation begins. User can approve, modify, or cancel.

    FAST  — Manager executes immediately without waiting for plan approval.
            Best for simple, well-defined tasks.
    """

    PLAN = "plan"
    FAST = "fast"


# Human-readable labels and descriptions for the mode picker
MODE_METADATA = {
    ExecutionMode.PLAN: {
        "label": "Plan",
        "icon": "📋",
        "tagline": "Agent can plan before executing tasks.",
        "detail": "Use for deep research, complex tasks, or collaborative work.",
        "color": "color(39)",  # cyan
    },
    ExecutionMode.FAST: {
        "label": "Fast",
        "icon": "⚡",
        "tagline": "Agent will execute tasks directly.",
        "detail": "Use for simple tasks that can be completed faster.",
        "color": "color(226)",  # yellow
    },
}

# Human-readable labels for each model
MODEL_METADATA = {
    # Google
    "gemini-2.5-pro-high": {
        "label": "Gemini 2.5 Pro (High)",
        "provider": "Google",
        "icon": "🔵",
        "tier": "premium",
    },
    "gemini-2.5-pro-low": {
        "label": "Gemini 2.5 Pro (Low)",
        "provider": "Google",
        "icon": "🔵",
        "tier": "standard",
    },
    "gemini-2.5-flash": {
        "label": "Gemini 2.5 Flash",
        "provider": "Google",
        "icon": "🔵",
        "tier": "fast",
    },
    "gemini-2.0-flash-exp": {
        "label": "Gemini 2.0 Flash",
        "provider": "Google",
        "icon": "🔵",
        "tier": "fast",
    },
    "gemini-pro": {"label": "Gemini Pro", "provider": "Google", "icon": "🔵", "tier": "standard"},
    # Anthropic
    "claude-opus-4-6-thinking": {
        "label": "Claude Opus 4.6 (Thinking)",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "premium",
    },
    "claude-sonnet-4-6": {
        "label": "Claude Sonnet 4.6",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "standard",
    },
    "claude-sonnet-4-5-thinking": {
        "label": "Claude Sonnet 4.5 (Thinking)",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "standard",
    },
    "claude-sonnet-4-5": {
        "label": "Claude Sonnet 4.5",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "standard",
    },
    "claude-3-5-sonnet-20241022": {
        "label": "Claude Sonnet 3.5",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "standard",
    },
    "claude-3-opus-20240229": {
        "label": "Claude Opus 3",
        "provider": "Anthropic",
        "icon": "🟠",
        "tier": "premium",
    },
    # OpenAI
    "o1": {"label": "o1", "provider": "OpenAI", "icon": "🟢", "tier": "premium"},
    "o3-mini": {"label": "o3-mini", "provider": "OpenAI", "icon": "🟢", "tier": "fast"},
    "gpt-4o": {"label": "GPT-4o", "provider": "OpenAI", "icon": "🟢", "tier": "standard"},
    "gpt-4o-mini": {"label": "GPT-4o Mini", "provider": "OpenAI", "icon": "🟢", "tier": "fast"},
    "gpt-4-turbo": {"label": "GPT-4 Turbo", "provider": "OpenAI", "icon": "🟢", "tier": "standard"},
    "gpt-4": {"label": "GPT-4", "provider": "OpenAI", "icon": "🟢", "tier": "standard"},
    # OSS
    "gpt-oss-120b-medium": {
        "label": "GPT-OSS 120B (Medium)",
        "provider": "OSS",
        "icon": "⚪",
        "tier": "standard",
    },
    # Auto
    "auto": {"label": "Auto (Manager decides)", "provider": "Archon", "icon": "🤖", "tier": "auto"},
}

# Ordered list for the picker (matches screenshot order)
MODEL_PICKER_ORDER = [
    "auto",
    "gemini-2.5-pro-high",
    "gemini-2.5-pro-low",
    "gemini-2.5-flash",
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-thinking",
    "claude-sonnet-4-6",
    "claude-opus-4-6-thinking",
    "gpt-oss-120b-medium",
    "o1",
    "o3-mini",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gemini-2.0-flash-exp",
    "gemini-pro",
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "gpt-4",
]


@dataclass
class SessionConfig:
    """
    Holds the user's chosen settings for the current ARCHON session.
    Created once at startup via the interactive pickers and passed
    through the REPL loop.
    """

    mode: ExecutionMode = ExecutionMode.PLAN
    model: str = "auto"  # model ID string, "auto" = Manager decides
    project_name: str = "Unknown"

    @property
    def mode_label(self) -> str:
        return MODE_METADATA[self.mode]["label"]

    @property
    def mode_icon(self) -> str:
        return MODE_METADATA[self.mode]["icon"]

    @property
    def model_label(self) -> str:
        meta = MODEL_METADATA.get(self.model, {})
        return meta.get("label", self.model)

    @property
    def model_provider(self) -> str:
        meta = MODEL_METADATA.get(self.model, {})
        return meta.get("provider", "Unknown")

    @property
    def model_icon(self) -> str:
        meta = MODEL_METADATA.get(self.model, {})
        return meta.get("icon", "•")

    @property
    def is_auto_model(self) -> bool:
        return self.model == "auto"

    def summary_line(self) -> str:
        """One-line summary for status bar display."""
        return f"{self.mode_icon} {self.mode_label}  ·  {self.model_icon} {self.model_label}"
