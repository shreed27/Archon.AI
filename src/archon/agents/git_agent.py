"""
Git Agent - handles version control operations and git workflow management.
"""

import re
from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# Conventional commit types
CONVENTIONAL_COMMIT_TYPES = [
    "feat",
    "fix",
    "docs",
    "style",
    "refactor",
    "perf",
    "test",
    "build",
    "ci",
    "chore",
    "revert",
]

CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)" r"(\(.+\))?(!)?:\s.+"
)


class GitAgent(BaseAgent):
    """
    Git agent handles:
    - Conventional commit message generation
    - Branch naming strategy
    - Pull request / merge request descriptions
    - Changelog generation (Keep a Changelog format)
    - Git conflict resolution guidance
    - Release tagging and versioning (SemVer)
    - .gitignore generation
    - Git hooks setup (pre-commit, pre-push)

    Primary model: Claude Sonnet (good at structured text generation)
    Tool fallbacks: None (git operations are lightweight)
    """

    PREFERRED_MODEL = ModelType.CLAUDE_SONNET

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute git workflow task."""

        self.logger.info(f"Executing git task: {task.description}")

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
        """Build prompt for git task."""

        operation = task.context.get("operation", "commit")
        diff_summary = task.context.get("diff_summary", "")
        changed_files = task.context.get("changed_files", [])
        current_version = task.context.get("current_version", "0.0.0")
        branch_type = task.context.get("branch_type", "feature")

        return f"""
You are a senior software engineer with deep expertise in git workflows and version control best practices.

Task: {task.description}

Context:
{task.context}

Operation: {operation}
Current Version: {current_version}
Branch Type: {branch_type}
Changed Files: {changed_files}
Diff Summary: {diff_summary}

Conventional Commit Types: {CONVENTIONAL_COMMIT_TYPES}

Generate git workflow artifacts covering:
1. Commit messages (Conventional Commits format: type(scope): description)
2. Branch name (kebab-case: type/short-description)
3. Pull request title and description (with checklist)
4. Changelog entry (Keep a Changelog format)
5. Version bump recommendation (SemVer: major/minor/patch)
6. Git configuration files (.gitignore, .gitattributes) if needed
7. Pre-commit hook scripts if needed

Rules:
- Commit messages: imperative mood, max 72 chars subject line
- Branch names: lowercase, hyphens only, max 50 chars
- PR descriptions: include what changed, why, how to test, screenshots if UI
- Changelog: group by Added/Changed/Deprecated/Removed/Fixed/Security

Return JSON format:
{{
    "commits": [
        {{
            "message": "feat(auth): add JWT refresh token rotation",
            "type": "feat",
            "scope": "auth",
            "breaking": false,
            "body": "...",
            "footer": ""
        }}
    ],
    "branch_name": "feat/jwt-refresh-token-rotation",
    "pull_request": {{
        "title": "feat(auth): add JWT refresh token rotation",
        "description": "...",
        "checklist": [...],
        "labels": ["enhancement", "security"]
    }},
    "changelog_entry": {{
        "version": "1.1.0",
        "date": "{datetime.now().strftime('%Y-%m-%d')}",
        "added": [...],
        "changed": [...],
        "fixed": [...],
        "security": [...]
    }},
    "version_bump": {{
        "current": "{current_version}",
        "recommended": "patch",
        "new_version": "0.0.1",
        "reason": "..."
    }},
    "files": []
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate git output."""

        if "commits" not in output:
            self.logger.warning("Output missing 'commits' field")
            return False

        # Validate commit messages follow Conventional Commits
        for commit in output.get("commits", []):
            message = commit.get("message", "")
            if not CONVENTIONAL_COMMIT_PATTERN.match(message):
                self.logger.warning(
                    f"Commit message does not follow Conventional Commits: '{message}'"
                )
                return False

            # Check subject line length
            subject = message.split("\n")[0]
            if len(subject) > 72:
                self.logger.warning(f"Commit subject too long ({len(subject)} chars): '{subject}'")
                return False

        # Validate branch name
        branch = output.get("branch_name", "")
        if branch and not re.match(r"^[a-z0-9/_-]+$", branch):
            self.logger.warning(f"Invalid branch name format: '{branch}'")
            return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on git artifact completeness."""

        score = 0.4

        if output.get("commits"):
            score += 0.1
        if output.get("branch_name"):
            score += 0.1
        if output.get("pull_request", {}).get("description"):
            score += 0.15
        if output.get("changelog_entry"):
            score += 0.15
        if output.get("version_bump"):
            score += 0.1

        return min(score, 1.0)

    def _extract_file_changes(self, output: dict) -> list:
        """Extract file changes (e.g., .gitignore, hooks) from output."""

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

    def get_commit_messages(self, output: dict) -> list[str]:
        """Return list of formatted commit messages from output."""

        return [c.get("message", "") for c in output.get("commits", [])]

    async def propose_alternative(self, task: Task) -> dict:
        """Propose trunk-based development alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "trunk_based_development",
            "reasoning": (
                "Use trunk-based development with short-lived feature branches (< 2 days). "
                "Reduces merge conflicts, enables continuous integration, "
                "and keeps the main branch always deployable."
            ),
            "risk_score": 0.2,
            "complexity_score": 0.25,
            "estimated_time_hours": 2.0,
            "dependencies": ["pre-commit", "commitlint"],
        }


# Register agent
register_agent(AgentType.GIT, GitAgent)
