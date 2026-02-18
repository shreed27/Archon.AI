"""
Architect Agent - handles high-level system design, ADRs, and tech stack decisions.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# Architecture patterns
ARCHITECTURE_PATTERNS = [
    "monolith",
    "modular_monolith",
    "microservices",
    "event_driven",
    "serverless",
    "hexagonal",
    "cqrs_event_sourcing",
    "layered",
    "clean_architecture",
]

# Architecture quality attributes (ISO 25010)
QUALITY_ATTRIBUTES = [
    "scalability",
    "reliability",
    "maintainability",
    "security",
    "performance",
    "observability",
    "deployability",
    "testability",
    "cost_efficiency",
]

# ADR status options
ADR_STATUSES = ["proposed", "accepted", "deprecated", "superseded"]


class ArchitectAgent(BaseAgent):
    """
    Architect agent handles:
    - High-level system architecture design
    - Architecture Decision Records (ADRs)
    - Tech stack selection with trade-off analysis
    - Scalability and capacity planning
    - System decomposition (bounded contexts, service boundaries)
    - API contract design (REST, GraphQL, gRPC)
    - Event-driven architecture design (topics, schemas, consumers)
    - Observability architecture (tracing, metrics, logging)
    - Disaster recovery and business continuity planning
    - Architecture review and risk assessment

    Primary model: Claude Opus (deepest reasoning for complex trade-offs)
    Tool fallbacks: Eraser CLI (architecture diagrams)

    Note: The Architect Agent PROPOSES — the Manager DECIDES.
    This agent never unilaterally implements; it produces design artifacts
    that feed into the deliberation system.
    """

    PREFERRED_MODEL = ModelType.CLAUDE_OPUS

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute architecture design task."""

        self.logger.info(f"Executing architect task: {task.description}")

        start_time = datetime.now()

        prompt = self._build_prompt(task)
        response = await self._call_model(model, prompt)
        output = response.get("parsed_json", response)

        is_valid = await self.validate_output(output)

        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Architecture decisions are high-value — reflect in quality score
        result = TaskResult(
            task_id=task.task_id,
            success=is_valid,
            output=output,
            files_modified=self._extract_file_changes(output),
            quality_score=self._compute_quality_score(output) if is_valid else 0.3,
            execution_time_ms=execution_time_ms,
            model_used=model.value,
            architecture_changes=output.get("architecture_summary"),
        )

        return result

    def _build_prompt(self, task: Task) -> str:
        """Build prompt for architecture task."""

        operation = task.context.get(
            "operation", "design"
        )  # design | review | adr | decompose | api_contract
        project_phase = task.context.get(
            "project_phase", "mvp"
        )  # mvp | growth | scale | enterprise
        team_size = task.context.get("team_size", 3)
        constraints = task.context.get("constraints", [])
        existing_architecture = task.context.get("existing_architecture", "")
        quality_priorities = task.context.get(
            "quality_priorities", ["scalability", "maintainability"]
        )

        return f"""
You are a principal software architect with 15+ years of experience designing large-scale distributed systems.

Task: {task.description}

Context:
{task.context}

Operation: {operation}
Project Phase: {project_phase}
Team Size: {team_size} engineers
Constraints: {constraints}
Existing Architecture: {existing_architecture or "Greenfield"}
Quality Priorities (in order): {quality_priorities}

Available architecture patterns:
{chr(10).join(f"- {p}" for p in ARCHITECTURE_PATTERNS)}

Quality attributes to evaluate:
{chr(10).join(f"- {qa}" for qa in QUALITY_ATTRIBUTES)}

Provide a comprehensive architecture design covering:
1. Recommended architecture pattern with justification
2. System components and their responsibilities
3. Service boundaries and communication protocols
4. Data flow and storage strategy
5. API contracts (REST/GraphQL/gRPC endpoints)
6. Event/message schema design (if event-driven)
7. Observability strategy (distributed tracing, metrics, structured logging)
8. Scalability plan (horizontal/vertical, auto-scaling triggers)
9. Architecture Decision Records (ADRs) for key decisions
10. Risk assessment and mitigation strategies
11. Migration path from existing architecture (if applicable)
12. Mermaid diagram descriptions

IMPORTANT: For each major decision, provide:
- Options considered
- Trade-offs evaluated
- Chosen approach and rationale
- Conditions that would change this decision

Return JSON format:
{{
    "architecture": {{
        "pattern": "modular_monolith",
        "justification": "...",
        "components": [
            {{
                "name": "UserService",
                "responsibility": "...",
                "technology": "FastAPI",
                "owns_data": ["users", "sessions"],
                "exposes_api": true,
                "consumes_events": [],
                "produces_events": ["user.created", "user.updated"]
            }}
        ],
        "communication": {{
            "sync": "REST/HTTP",
            "async": "None at MVP phase"
        }},
        "data_strategy": "..."
    }},
    "adrs": [
        {{
            "id": "ADR-001",
            "title": "Use PostgreSQL as primary database",
            "status": "accepted",
            "context": "...",
            "decision": "...",
            "consequences": {{
                "positive": [...],
                "negative": [...],
                "risks": [...]
            }},
            "alternatives_considered": [...]
        }}
    ],
    "api_contracts": [
        {{
            "service": "UserService",
            "protocol": "REST",
            "endpoints": [
                {{
                    "method": "POST",
                    "path": "/users",
                    "request_schema": {{}},
                    "response_schema": {{}},
                    "auth_required": true
                }}
            ]
        }}
    ],
    "observability": {{
        "tracing": "OpenTelemetry + Jaeger",
        "metrics": "Prometheus + Grafana",
        "logging": "Structured JSON + ELK",
        "alerting": "PagerDuty"
    }},
    "scalability_plan": {{
        "current_capacity": "...",
        "scaling_triggers": [...],
        "bottlenecks": [...],
        "target_capacity": "..."
    }},
    "risks": [
        {{
            "risk": "...",
            "probability": "medium",
            "impact": "high",
            "mitigation": "..."
        }}
    ],
    "migration_plan": null,
    "files": [
        {{
            "path": "docs/architecture/ARCHITECTURE.md",
            "content": "...",
            "change_type": "create"
        }},
        {{
            "path": "docs/architecture/decisions/ADR-001.md",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "architecture_summary": {{
        "pattern": "modular_monolith",
        "component_count": 0,
        "adr_count": 0,
        "risk_count": 0
    }},
    "diagrams": [
        {{
            "title": "System Context Diagram",
            "mermaid": "graph TD\\n    User --> API\\n    API --> DB"
        }}
    ]
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate architecture output."""

        if "architecture" not in output:
            self.logger.warning("Output missing 'architecture' field")
            return False

        arch = output["architecture"]
        if not arch.get("pattern"):
            self.logger.warning("Architecture missing 'pattern'")
            return False

        if arch.get("pattern") not in ARCHITECTURE_PATTERNS:
            self.logger.warning(f"Unknown architecture pattern: {arch.get('pattern')}")
            # Don't fail — model may propose a valid unlisted pattern
            pass

        if not arch.get("components"):
            self.logger.warning("Architecture has no components defined")
            return False

        # Validate ADRs
        for adr in output.get("adrs", []):
            if not all(k in adr for k in ["id", "title", "status", "decision"]):
                self.logger.warning(f"ADR missing required fields: {adr.get('id', 'unknown')}")
                return False

            if adr.get("status") not in ADR_STATUSES:
                self.logger.warning(f"Invalid ADR status: {adr.get('status')}")
                return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on architectural completeness and depth."""

        score = 0.3

        arch = output.get("architecture", {})
        components = arch.get("components", [])

        if components:
            # Reward components that define data ownership
            with_data = sum(1 for c in components if c.get("owns_data"))
            score += 0.05 * (with_data / max(len(components), 1))

        adrs = output.get("adrs", [])
        if adrs:
            # Reward ADRs that document alternatives considered
            with_alternatives = sum(1 for a in adrs if a.get("alternatives_considered"))
            score += 0.1 * (with_alternatives / max(len(adrs), 1))
            score += min(0.1, len(adrs) * 0.025)  # More ADRs = more thorough

        if output.get("api_contracts"):
            score += 0.1
        if output.get("observability"):
            score += 0.1
        if output.get("scalability_plan"):
            score += 0.1
        if output.get("risks"):
            score += 0.1
        if output.get("diagrams"):
            score += 0.05

        return min(score, 1.0)

    def _extract_file_changes(self, output: dict) -> list:
        """Extract file changes (architecture docs, ADR files) from output."""

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

    def get_adrs(self, output: dict) -> list:
        """Return all Architecture Decision Records from output."""
        return output.get("adrs", [])

    def get_risks(self, output: dict) -> list:
        """Return all identified architectural risks."""
        return output.get("risks", [])

    async def propose_alternative(self, task: Task) -> dict:
        """Propose clean architecture / ports-and-adapters alternative."""

        return {
            "agent": self.agent_type.value,
            "proposal": "clean_architecture_ports_adapters",
            "reasoning": (
                "Clean Architecture with Ports & Adapters (Hexagonal) isolates business logic "
                "from infrastructure concerns. Makes the system independently testable, "
                "allows swapping databases/frameworks without touching domain logic, "
                "and enforces clear dependency direction."
            ),
            "risk_score": 0.2,
            "complexity_score": 0.5,
            "estimated_time_hours": 16.0,
            "dependencies": [],
        }


# Register agent
register_agent(AgentType.ARCHITECT, ArchitectAgent)
