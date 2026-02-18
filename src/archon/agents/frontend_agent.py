"""
Frontend Agent - handles UI/UX development tasks.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class FrontendAgent(BaseAgent):
    """
    Frontend agent handles:
    - React/Vue/Svelte component development
    - CSS/styling and design systems
    - Accessibility (a11y) compliance
    - State management
    - Frontend testing (unit + E2E)
    - Performance optimization

    Primary model: Gemini Flash (fast iteration on UI)
    Tool fallbacks: Figma CLI, Playwright
    """

    PREFERRED_MODEL = ModelType.GEMINI_FLASH

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute frontend development task."""

        self.logger.info(f"Executing frontend task: {task.description}")

        start_time = datetime.now()

        prompt = self._build_prompt(task)
        response = await self._call_model(model, prompt)
        output = response.get("parsed_json", response)

        is_valid = await self.validate_output(output)

        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        result = TaskResult(
            task_id=task.task_id,
            success=is_valid,
            output=output,
            files_modified=self._extract_file_changes(output),
            quality_score=self._compute_quality_score(output) if is_valid else 0.3,
            execution_time_ms=execution_time_ms,
            model_used=model.value,
        )

        return result

    def _build_prompt(self, task: Task) -> str:
        """Build prompt for frontend task."""

        framework = task.context.get("framework", "React")
        styling = task.context.get("styling", "CSS Modules")
        a11y_required = task.context.get("a11y", True)

        return f"""
You are a senior frontend engineer specializing in {framework} and modern UI/UX.

Task: {task.description}

Context:
{task.context}

Framework: {framework}
Styling: {styling}
Accessibility required: {a11y_required}

Provide a complete implementation with:
1. Component files (with full paths and complete code)
2. Styles (CSS/SCSS/styled-components)
3. Accessibility attributes (aria-*, role, tabIndex)
4. Unit tests using Jest/Testing Library
5. Storybook stories (if applicable)
6. Performance notes (memoization, lazy loading)

Return JSON format:
{{
    "files": [
        {{
            "path": "src/components/Button/Button.tsx",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "components": [
        {{
            "name": "Button",
            "props": [...],
            "accessibility_score": 0.95,
            "reusability_score": 0.9
        }}
    ],
    "styles": [...],
    "tests": [...],
    "performance_notes": "..."
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate frontend output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Warn if no components defined
        if not output.get("components"):
            self.logger.warning("No component metadata in output")

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on output completeness."""

        score = 0.5  # base

        if output.get("files"):
            score += 0.1
        if output.get("tests"):
            score += 0.15
        if output.get("styles"):
            score += 0.1

        # Reward accessibility
        components = output.get("components", [])
        if components:
            avg_a11y = sum(c.get("accessibility_score", 0) for c in components) / len(components)
            score += 0.15 * avg_a11y

        return min(score, 1.0)

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

    async def propose_alternative(self, task: Task) -> dict:
        """Propose frontend architecture alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "component_library_approach",
            "reasoning": (
                "Build reusable component library first to ensure consistency, "
                "reduce duplication, and improve long-term maintainability."
            ),
            "risk_score": 0.2,
            "complexity_score": 0.4,
            "estimated_time_hours": 8.0,
            "dependencies": ["storybook", "jest", "testing-library"],
        }


# Register agent
register_agent(AgentType.FRONTEND, FrontendAgent)
