"""
Eraser.io CLI Tool - Generate diagrams from text.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import shlex

from archon.tools.base import BaseTool, ToolSchema
from archon.utils.schemas import ToolResult, Tool
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class EraserCLITool(BaseTool):
    """
    Wrapper for eraser-cli to generate diagrams.
    Requires: npm install -g eraser-cli
    """

    def __init__(self, sandbox):
        super().__init__(sandbox)
        self.name = "eraser_cli"
        self.description = "Generate implementation of diagrams using eraser-cli"
        self.output_dir = sandbox.project_root / ".archon" / "artifacts" / "diagrams"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trust_score = 0.95  # Highly trusted visualization tool

    async def validate(self) -> bool:
        """Check if eraser-cli is installed."""
        res = await self.sandbox.execute("npm list -g eraser-cli", "npm list -g eraser-cli")
        if not res.success or "empty" in res.output:
            # Try check execution
            res = await self.sandbox.execute("eraser", "eraser --version")
            return res.success
        return True

    async def execute(self, input_data: Dict[str, Any]) -> ToolResult:
        """
        Generate diagram.
        Input: {"dsl": "string content", "filename": "output.png", "type": "sequence|flowchart|etc"}
        """
        dsl_content = input_data.get("dsl")
        filename = input_data.get("filename", "diagram.png")

        if not dsl_content:
            return ToolResult(success=False, error="Missing 'dsl' content")

        # Write DSL to temp file
        temp_dsl = self.output_dir / f"{Path(filename).stem}.eraser"
        temp_dsl.write_text(dsl_content)

        # Construct command
        # eraser-cli [path/to/file.eraser] --output [path/to/output.png]
        output_path = self.output_dir / filename
        cmd = f"eraser {shlex.quote(str(temp_dsl))} --output {shlex.quote(str(output_path))}"

        logger.info(f"Generating diagram: {cmd}")
        result = await self.sandbox.execute("eraser_cli", cmd)

        if result.success:
            result.output = f"Diagram saved to {output_path}"
            result.artifacts = [str(output_path)]

        return result
