"""
Testing Agent - handles test generation, coverage analysis, and E2E testing.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class TestingAgent(BaseAgent):
    """
    Testing agent handles:
    - Unit test generation (pytest, Jest, Vitest)
    - Integration test generation
    - E2E test generation (Playwright, Cypress)
    - Test coverage analysis and gap identification
    - Test data/fixture generation
    - Performance/load test scripts
    - Mutation testing recommendations

    Primary model: GPT-4 (strong at understanding code semantics for test generation)
    Tool fallbacks: Playwright CLI
    """

    PREFERRED_MODEL = ModelType.GPT4

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute testing task."""

        self.logger.info(f"Executing testing task: {task.description}")

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
        """Build prompt for testing task."""

        test_framework = task.context.get("test_framework", "pytest")
        coverage_target = task.context.get("coverage_target", 0.80)
        test_types = task.context.get("test_types", ["unit", "integration"])
        source_files = task.context.get("source_files", [])

        return f"""
You are a senior QA engineer and test architect with expertise in test-driven development.

Task: {task.description}

Context:
{task.context}

Test Framework: {test_framework}
Coverage Target: {coverage_target * 100:.0f}%
Test Types Required: {test_types}
Source Files to Test: {source_files}

Generate comprehensive tests covering:
1. Unit tests (happy path, edge cases, error cases)
2. Integration tests (component interactions, API contracts)
3. E2E tests (critical user journeys) — if applicable
4. Test fixtures and factories
5. Mock/stub definitions
6. Coverage report (estimated coverage per file)

Testing principles to follow:
- AAA pattern (Arrange, Act, Assert)
- One assertion per test where possible
- Descriptive test names (should_do_X_when_Y)
- No test interdependencies
- Fast execution (mock external services)

Return JSON format:
{{
    "files": [
        {{
            "path": "tests/unit/test_users.py",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "test_summary": {{
        "total_tests": 0,
        "unit_tests": 0,
        "integration_tests": 0,
        "e2e_tests": 0,
        "estimated_coverage": 0.0,
        "coverage_by_file": {{}}
    }},
    "fixtures": [...],
    "mocks": [...],
    "coverage_gaps": [
        {{
            "file": "src/api/users.py",
            "uncovered_lines": [...],
            "reason": "..."
        }}
    ]
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate testing output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Ensure at least one test file was generated
        test_files = [f for f in output.get("files", []) if "test" in f.get("path", "").lower()]
        if not test_files:
            self.logger.warning("No test files found in output")
            return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on test completeness."""

        score = 0.4

        summary = output.get("test_summary", {})
        estimated_coverage = summary.get("estimated_coverage", 0.0)

        # Coverage contribution (up to 0.3)
        score += 0.3 * min(estimated_coverage, 1.0)

        if output.get("fixtures"):
            score += 0.1
        if output.get("mocks"):
            score += 0.1
        if output.get("coverage_gaps") is not None:
            score += 0.1  # Reward identifying gaps

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

    def get_estimated_coverage(self, output: dict) -> float:
        """Return estimated test coverage from output."""

        return output.get("test_summary", {}).get("estimated_coverage", 0.0)

    async def propose_alternative(self, task: Task) -> dict:
        """Propose TDD-first testing alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "tdd_red_green_refactor",
            "reasoning": (
                "Write failing tests first (red), implement minimum code to pass (green), "
                "then refactor. This ensures 100% test coverage by design and "
                "forces clean API design."
            ),
            "risk_score": 0.15,
            "complexity_score": 0.35,
            "estimated_time_hours": 10.0,
            "dependencies": ["pytest", "pytest-cov", "playwright"],
        }


# Register agent
register_agent(AgentType.TESTING, TestingAgent)
