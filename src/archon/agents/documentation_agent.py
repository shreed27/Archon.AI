"""
Documentation Agent - handles all documentation generation tasks.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class DocumentationAgent(BaseAgent):
    """
    Documentation agent handles:
    - README generation (project, module, API)
    - API documentation (OpenAPI/Swagger specs)
    - Architecture documentation (ADRs, system design docs)
    - Inline docstrings and type annotations
    - Changelog generation
    - Runbooks and operational guides
    - Onboarding guides

    Primary model: Gemini Pro (1M context window for large codebases)
    Tool fallbacks: Eraser CLI (architecture diagrams)
    """

    PREFERRED_MODEL = ModelType.GEMINI_PRO

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute documentation task."""

        self.logger.info(f"Executing documentation task: {task.description}")

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
        """Build prompt for documentation task."""

        doc_type = task.context.get("doc_type", "readme")
        project_name = task.context.get("project_name", "Project")
        audience = task.context.get("audience", "developers")
        source_files = task.context.get("source_files", [])
        existing_docs = task.context.get("existing_docs", [])

        return f"""
You are a senior technical writer and documentation engineer.

Task: {task.description}

Context:
{task.context}

Documentation Type: {doc_type}
Project Name: {project_name}
Target Audience: {audience}
Source Files: {source_files}
Existing Documentation: {existing_docs}

Generate comprehensive documentation covering:
1. Project/module overview and purpose
2. Installation and setup instructions
3. Usage examples (with code snippets)
4. API reference (if applicable)
5. Architecture overview
6. Contributing guidelines
7. Changelog (if applicable)

Documentation quality standards:
- Clear, concise language (avoid jargon without explanation)
- Working code examples
- Diagrams described in Mermaid syntax where helpful
- Consistent formatting (Markdown)
- Version-specific information where relevant

Return JSON format:
{{
    "files": [
        {{
            "path": "README.md",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "doc_summary": {{
        "total_docs": 0,
        "doc_types": [],
        "word_count": 0,
        "has_code_examples": true,
        "has_diagrams": false
    }},
    "api_spec": null,
    "architecture_decisions": [],
    "diagrams": []
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate documentation output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

            # Ensure documentation files have meaningful content
            content = file.get("content", "")
            if len(content.strip()) < 100:
                self.logger.warning(f"Documentation file too short: {file['path']}")
                return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on documentation completeness."""

        score = 0.4

        summary = output.get("doc_summary", {})

        if summary.get("has_code_examples"):
            score += 0.15
        if summary.get("has_diagrams"):
            score += 0.1
        if output.get("api_spec"):
            score += 0.1
        if output.get("architecture_decisions"):
            score += 0.1

        # Word count contribution (reward thoroughness, cap at 5000 words)
        word_count = summary.get("word_count", 0)
        score += 0.15 * min(word_count / 5000, 1.0)

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
        """Propose docs-as-code alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "docs_as_code_with_ci",
            "reasoning": (
                "Treat documentation as code: store in version control, "
                "auto-generate API docs from source, validate in CI pipeline. "
                "Ensures docs stay in sync with code."
            ),
            "risk_score": 0.1,
            "complexity_score": 0.3,
            "estimated_time_hours": 4.0,
            "dependencies": ["mkdocs", "sphinx", "eraser-cli"],
        }


# Register agent
register_agent(AgentType.DOCUMENTATION, DocumentationAgent)
