"""
Integration Agent - handles third-party API integrations and service connections.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


class IntegrationAgent(BaseAgent):
    """
    Integration agent handles:
    - Third-party API integrations (REST, GraphQL, gRPC, WebSocket)
    - OAuth2 / SSO provider setup (Google, GitHub, Auth0)
    - Webhook implementation and event handling
    - Message queue integrations (Kafka, RabbitMQ, SQS)
    - Payment gateway integrations (Stripe, PayPal)
    - Email/SMS service integrations (SendGrid, Twilio)
    - SDK client generation and wrapper libraries
    - API contract validation and mocking

    Primary model: GPT-4 (strong at understanding API specs and generating client code)
    Tool fallbacks: None (integration work is primarily code generation)
    """

    PREFERRED_MODEL = ModelType.GPT4

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute integration task."""

        self.logger.info(f"Executing integration task: {task.description}")

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
        """Build prompt for integration task."""

        service_name = task.context.get("service_name", "External Service")
        integration_type = task.context.get("integration_type", "REST")
        auth_method = task.context.get("auth_method", "API Key")
        api_spec_url = task.context.get("api_spec_url", "")
        webhook_events = task.context.get("webhook_events", [])

        return f"""
You are a senior integration engineer specializing in connecting systems and third-party services.

Task: {task.description}

Context:
{task.context}

Service: {service_name}
Integration Type: {integration_type}
Authentication: {auth_method}
API Spec URL: {api_spec_url}
Webhook Events: {webhook_events}

Provide a complete integration implementation with:
1. Client library / SDK wrapper (typed, with error handling)
2. Authentication setup (OAuth2 flow, API key management, etc.)
3. Webhook handler (if applicable)
4. Retry logic with exponential backoff
5. Rate limiting / throttling handling
6. Integration tests with mocked responses
7. Environment variable configuration
8. Usage examples

Best practices:
- Never hardcode credentials — use environment variables
- Implement circuit breaker pattern for resilience
- Log all API calls (without sensitive data)
- Handle pagination for list endpoints
- Validate webhook signatures

Return JSON format:
{{
    "files": [
        {{
            "path": "src/integrations/{service_name.lower().replace(' ', '_')}/client.py",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "integration_summary": {{
        "service": "{service_name}",
        "integration_type": "{integration_type}",
        "auth_method": "{auth_method}",
        "endpoints_covered": [],
        "webhook_events_handled": [],
        "has_retry_logic": true,
        "has_rate_limiting": true
    }},
    "environment_variables": [
        {{
            "name": "SERVICE_API_KEY",
            "description": "API key for {service_name}",
            "required": true
        }}
    ],
    "tests": [...],
    "usage_examples": [...]
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate integration output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Ensure environment variables are documented
        if not output.get("environment_variables"):
            self.logger.warning(
                "No environment variables documented — possible hardcoded credentials risk"
            )

        # Check for hardcoded secrets in generated code
        for file in output.get("files", []):
            content = file.get("content", "").lower()
            for pattern in ['api_key = "', 'secret = "', 'password = "']:
                if pattern in content:
                    self.logger.warning(f"Possible hardcoded credential in {file['path']}")
                    return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on integration completeness."""

        score = 0.4

        summary = output.get("integration_summary", {})

        if summary.get("has_retry_logic"):
            score += 0.1
        if summary.get("has_rate_limiting"):
            score += 0.1
        if output.get("environment_variables"):
            score += 0.1
        if output.get("tests"):
            score += 0.15
        if output.get("usage_examples"):
            score += 0.15

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
        """Propose event-driven integration alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "event_driven_integration",
            "reasoning": (
                "Use an event-driven approach with message queues (SQS/Kafka) "
                "instead of direct API calls. This decouples services, improves "
                "resilience, and enables async processing."
            ),
            "risk_score": 0.25,
            "complexity_score": 0.5,
            "estimated_time_hours": 8.0,
            "dependencies": ["boto3", "kafka-python"],
        }


# Register agent
register_agent(AgentType.INTEGRATION, IntegrationAgent)
