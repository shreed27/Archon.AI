"""
DevOps Agent - handles infrastructure, CI/CD, and deployment tasks.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class DevOpsAgent(BaseAgent):
    """
    DevOps agent handles:
    - Infrastructure as Code (Terraform, Pulumi, CDK)
    - CI/CD pipeline configuration (GitHub Actions, GitLab CI)
    - Docker / Kubernetes manifests
    - Cloud resource provisioning (AWS, GCP, Azure)
    - Monitoring and alerting setup
    - Environment configuration management

    Primary model: Claude Sonnet (strong at structured config generation)
    Tool fallbacks: Terraform CLI, Pulumi CLI
    """

    PREFERRED_MODEL = ModelType.CLAUDE_SONNET

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute DevOps task."""

        self.logger.info(f"Executing devops task: {task.description}")

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
        """Build prompt for DevOps task."""

        cloud_provider = task.context.get("cloud_provider", "AWS")
        iac_tool = task.context.get("iac_tool", "Terraform")
        environment = task.context.get("environment", "production")
        container_runtime = task.context.get("container_runtime", "Docker")

        return f"""
You are a senior DevOps/SRE engineer with deep expertise in cloud infrastructure and automation.

Task: {task.description}

Context:
{task.context}

Cloud Provider: {cloud_provider}
IaC Tool: {iac_tool}
Environment: {environment}
Container Runtime: {container_runtime}

Provide a complete implementation with:
1. Infrastructure as Code files (Terraform/Pulumi/CDK)
2. CI/CD pipeline configuration (GitHub Actions / GitLab CI)
3. Docker/Kubernetes manifests (if applicable)
4. Environment variable templates (.env.example)
5. Monitoring/alerting configuration
6. Runbook documentation

Security requirements:
- No hardcoded secrets or credentials
- Least-privilege IAM policies
- Network segmentation where applicable

Return JSON format:
{{
    "files": [
        {{
            "path": "infra/main.tf",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "infrastructure": {{
        "resources": [...],
        "estimated_monthly_cost_usd": 0.0,
        "cloud_provider": "{cloud_provider}"
    }},
    "pipelines": [...],
    "environment_variables": [...],
    "runbook": "..."
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate DevOps output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Check for hardcoded secrets (basic heuristic)
        for file in output.get("files", []):
            content = file.get("content", "")
            suspicious_patterns = ["password=", "secret=", "api_key=", "AWS_SECRET_ACCESS_KEY="]
            for pattern in suspicious_patterns:
                if pattern.lower() in content.lower() and "example" not in file["path"]:
                    self.logger.warning(f"Possible hardcoded secret in {file['path']}")
                    return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on output completeness."""

        score = 0.5

        if output.get("files"):
            score += 0.1
        if output.get("infrastructure"):
            score += 0.1
        if output.get("pipelines"):
            score += 0.1
        if output.get("environment_variables"):
            score += 0.1
        if output.get("runbook"):
            score += 0.1

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
        """Propose DevOps architecture alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "managed_services_first",
            "reasoning": (
                "Use managed cloud services (RDS, ElastiCache, ECS) instead of "
                "self-managed infrastructure to reduce operational burden and improve reliability."
            ),
            "risk_score": 0.2,
            "complexity_score": 0.3,
            "estimated_time_hours": 6.0,
            "dependencies": ["terraform", "aws-cli"],
        }


# Register agent
register_agent(AgentType.DEVOPS, DevOpsAgent)
