"""
Tool Sandbox stub.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    output: Any
    execution_time_ms: int
    logs: str = ""


class ToolSandbox:
    def __init__(self, work_dir: Optional[Path] = None):
        self.work_dir = work_dir

    async def execute(self, tool: Any, context: Dict) -> ToolResult:
        return ToolResult(success=True, output={}, execution_time_ms=0)
