"""
Base Tool Interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from archon.utils.schemas import ToolResult


class ToolSchema(BaseModel):
    name: str
    description: str
    task_types: Optional[list[str]] = []
    trust_score: float = 0.8
    installation_command: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None


class BaseTool(ABC):
    """Abstract base class for all external tools."""

    name: str = "base_tool"
    description: str = "Base tool"

    def __init__(self, sandbox=None):
        self.sandbox = sandbox

    @abstractmethod
    async def execute(self, input_data: Any) -> ToolResult:
        """Execute the tool with given input."""
        pass

    @abstractmethod
    async def validate(self) -> bool:
        """Check if tool is installed and working."""
        pass
