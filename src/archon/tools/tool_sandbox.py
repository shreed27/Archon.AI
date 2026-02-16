"""
Tool Sandbox - Secure execution environment for external tools.
"""

import asyncio
import subprocess
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
import json
import tempfile
import shutil


@dataclass
class ToolResult:
    """Result of tool execution."""

    success: bool
    output: Any
    execution_time_ms: int
    logs: str = ""
    error: Optional[str] = None
    exit_code: int = 0


class ToolSandbox:
    """
    Sandboxed execution environment for external CLI tools.
    Provides isolation, timeout, and resource limits.
    """

    def __init__(self, work_dir: Optional[Path] = None, timeout_seconds: int = 300):
        self.work_dir = work_dir or Path.cwd()
        self.timeout_seconds = timeout_seconds
        self.max_output_size = 10 * 1024 * 1024  # 10MB

    async def execute(self, tool_config: Dict, context: Dict) -> ToolResult:
        """
        Execute a tool in sandboxed environment.

        Args:
            tool_config: Tool configuration with command and args
            context: Execution context

        Returns:
            ToolResult with execution outcome
        """
        start_time = time.time()

        try:
            # Validate tool config
            if "command" not in tool_config:
                return ToolResult(
                    success=False,
                    output={},
                    execution_time_ms=0,
                    error="Tool config missing 'command' field",
                )

            # Build command
            command = self._build_command(tool_config, context)

            # Execute in sandbox
            result = await self._execute_command(command)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return ToolResult(
                success=result["success"],
                output=result["output"],
                execution_time_ms=execution_time_ms,
                logs=result["logs"],
                error=result.get("error"),
                exit_code=result.get("exit_code", 0),
            )

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                output={},
                execution_time_ms=execution_time_ms,
                error=f"Sandbox execution error: {str(e)}",
            )

    async def execute_script(self, script_content: str, language: str = "python") -> ToolResult:
        """
        Execute a script in sandboxed environment.

        Args:
            script_content: Script code to execute
            language: Script language (python, bash, etc.)

        Returns:
            ToolResult with execution outcome
        """
        start_time = time.time()

        try:
            # Create temporary file for script
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=self._get_script_extension(language), delete=False
            ) as f:
                f.write(script_content)
                script_path = f.name

            try:
                # Build command to execute script
                command = self._get_script_command(language, script_path)

                # Execute
                result = await self._execute_command(command)

                execution_time_ms = int((time.time() - start_time) * 1000)

                return ToolResult(
                    success=result["success"],
                    output=result["output"],
                    execution_time_ms=execution_time_ms,
                    logs=result["logs"],
                    error=result.get("error"),
                )

            finally:
                # Clean up temp file
                Path(script_path).unlink(missing_ok=True)

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return ToolResult(
                success=False,
                output={},
                execution_time_ms=execution_time_ms,
                error=f"Script execution error: {str(e)}",
            )

    async def _execute_command(self, command: List[str]) -> Dict:
        """Execute command with timeout and resource limits."""
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.work_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )

                stdout_str = stdout.decode("utf-8", errors="replace")
                stderr_str = stderr.decode("utf-8", errors="replace")

                # Check output size
                if len(stdout_str) > self.max_output_size:
                    stdout_str = stdout_str[: self.max_output_size] + "\n[OUTPUT TRUNCATED]"

                success = process.returncode == 0

                # Try to parse output as JSON, fallback to text
                try:
                    output = json.loads(stdout_str)
                except json.JSONDecodeError:
                    output = {"stdout": stdout_str, "stderr": stderr_str}

                return {
                    "success": success,
                    "output": output,
                    "logs": f"STDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}",
                    "exit_code": process.returncode,
                    "error": stderr_str if not success else None,
                }

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "output": {},
                    "logs": "",
                    "error": f"Command timed out after {self.timeout_seconds}s",
                }

        except Exception as e:
            return {
                "success": False,
                "output": {},
                "logs": "",
                "error": f"Command execution failed: {str(e)}",
            }

    def _build_command(self, tool_config: Dict, context: Dict) -> List[str]:
        """Build command from tool config and context."""
        command = [tool_config["command"]]

        # Add arguments
        if "args" in tool_config:
            args = tool_config["args"]
            if isinstance(args, list):
                command.extend(args)
            elif isinstance(args, str):
                command.append(args)

        # Substitute context variables
        command = [self._substitute_vars(arg, context) for arg in command]

        return command

    def _substitute_vars(self, text: str, context: Dict) -> str:
        """Substitute variables in text from context."""
        result = text
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        return result

    def _get_script_extension(self, language: str) -> str:
        """Get file extension for script language."""
        extensions = {
            "python": ".py",
            "bash": ".sh",
            "javascript": ".js",
            "typescript": ".ts",
        }
        return extensions.get(language.lower(), ".txt")

    def _get_script_command(self, language: str, script_path: str) -> List[str]:
        """Get command to execute script."""
        commands = {
            "python": ["python3", script_path],
            "bash": ["bash", script_path],
            "javascript": ["node", script_path],
            "typescript": ["ts-node", script_path],
        }
        return commands.get(language.lower(), ["cat", script_path])

    async def validate_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is available in the system.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is available
        """
        try:
            result = await self._execute_command(["which", tool_name])
            return result["success"]
        except Exception:
            return False

    async def install_tool(self, tool_name: str, install_command: Optional[str] = None) -> bool:
        """
        Install a tool (requires appropriate permissions).

        Args:
            tool_name: Name of tool to install
            install_command: Custom install command

        Returns:
            True if installation successful
        """
        if install_command:
            command = install_command.split()
        else:
            # Default to npm for now
            command = ["npm", "install", "-g", tool_name]

        try:
            result = await self._execute_command(command)
            return result["success"]
        except Exception:
            return False
