"""
Backend Agent - handles backend development tasks.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class BackendAgent(BaseAgent):
    """
    Backend agent handles:
    - API development
    - Database design
    - Business logic
    - Authentication/authorization
    - Backend testing
    """

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute backend development task."""

        self.logger.info(f"Executing backend task: {task.description}")

        start_time = datetime.now()

        # Build prompt for model
        prompt = self._build_prompt(task)

        # Call model
        response = await self._call_model(model, prompt)

        # Parse response
        output = response.get("parsed_json", response)

        # Validate output
        is_valid = await self.validate_output(output)

        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Build result
        result = TaskResult(
            task_id=task.task_id,
            success=is_valid,
            output=output,
            files_modified=self._extract_file_changes(output),
            quality_score=0.85 if is_valid else 0.3,
            execution_time_ms=execution_time_ms,
            model_used=model.value,
        )

        return result

    def _build_prompt(self, task: Task) -> str:
        """Build prompt for backend task."""

        return f"""
You are a senior backend engineer working on a production system.

Task: {task.description}

Context:
{task.context}

Provide a complete implementation with:
1. Code files (with full paths)
2. Database schema changes (if needed)
3. API endpoints (if needed)
4. Tests
5. Documentation

Return JSON format:
{{
    "files": [
        {{
            "path": "src/api/users.py",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "database_changes": [...],
    "api_endpoints": [...],
    "tests": [...]
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate backend output."""

        # Check required fields
        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        # Check each file has required fields
        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        return True

    def _extract_file_changes(self, output: dict) -> list:
        """Extract file changes from output."""

        changes = []

        for file in output.get("files", []):
            changes.append(
                FileChange(
                    path=file["path"],
                    change_type=file["change_type"],
                    lines_added=len(file.get("content", "").split("\n")),
                    lines_removed=0,
                    agent=self.agent_type.value,
                )
            )

        return changes


# Register agent
register_agent(AgentType.BACKEND, BackendAgent)
