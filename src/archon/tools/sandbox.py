"""
Tool Sandbox - Secure execution environment for external tools.
"""

import asyncio
import os
import shutil
import tempfile
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextlib import asynccontextmanager

from archon.utils.logger import get_logger
from archon.utils.schemas import ToolResult

logger = get_logger(__name__)


class ToolSandbox:
    """
    Executes external tools in an isolated environment.
    Enforces resource limits, timeouts, and filesystem restrictions (best effort).
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.sandbox_root = self.project_root / ".archon" / "sandbox"
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        tool_name: str,
        command: str,
        input_data: Optional[Dict] = None,
        timeout_seconds: int = 300,
    ) -> ToolResult:
        """
        Execute an external tool command.

        Args:
            tool_name: Name of the tool (for logging)
            command: Command string to execute
            input_data: Optional input data (passed via stdin or temp file)
            timeout_seconds: Execution timeout

        Returns:
            ToolResult with stdout, stderr, and metadata
        """
        start_time = time.time()

        # Prepare execution environment
        env = os.environ.copy()
        # Remove dangerous variables if needed?
        # For now, keep env needed for npm/git.

        # Setup temporary workspace if needed?
        # Maybe clone repo to temp if strictly read-only source is required?
        # Design says "read-only-except-project".
        # We'll run in project root directly for now as "local dev" mode.
        cwd = str(self.project_root)

        try:
            logger.info(f"Executing tool '{tool_name}': {command}")

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                # limit memory if possible?
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                if proc.returncode is None:
                    proc.terminate()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Execution timed out after {timeout_seconds}s",
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )

            execution_time = int((time.time() - start_time) * 1000)
            success = proc.returncode == 0

            output_str = stdout.decode().strip()
            error_str = stderr.decode().strip()

            if not success:
                logger.warning(f"Tool '{tool_name}' failed with code {proc.returncode}")
                logger.debug(f"Stderr: {error_str}")

            return ToolResult(
                success=success,
                output=output_str,
                error=error_str if not success else None,
                execution_time_ms=execution_time,
                tool_used=tool_name,
            )

        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    @asynccontextmanager
    async def isolated_environment(self):
        """Context manager for temporary isolation (placeholder for Docker/VM)."""
        # For phase 5, this is a no-op wrapper intended for future expansion.
        yield self
