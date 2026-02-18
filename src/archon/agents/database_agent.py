"""
Database Agent - handles schema design, migrations, query optimization, and data modeling.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# Supported database engines
SUPPORTED_ENGINES = [
    "postgresql",
    "mysql",
    "sqlite",
    "mongodb",
    "redis",
    "cassandra",
    "dynamodb",
    "bigquery",
]

# Common anti-patterns to flag
SCHEMA_ANTIPATTERNS = [
    "EAV (Entity-Attribute-Value) without justification",
    "Storing comma-separated values in a single column",
    "Missing foreign key constraints",
    "No indexes on foreign keys",
    "Storing JSON blobs where relational structure is appropriate",
    "Missing NOT NULL constraints on required fields",
    "Using TEXT for all string columns without length limits",
    "Missing created_at / updated_at audit columns",
]


class DatabaseAgent(BaseAgent):
    """
    Database agent handles:
    - Schema design (relational, document, key-value, time-series)
    - Migration scripts (Alembic, Flyway, Liquibase, Prisma)
    - Query optimization (EXPLAIN ANALYZE, index recommendations)
    - Index strategy (B-tree, GIN, GiST, partial indexes)
    - Normalization / denormalization trade-offs
    - Connection pooling configuration
    - Replication and sharding strategies
    - Data archival and partitioning
    - Seed data and fixture generation

    Primary model: Claude Opus (best at complex relational reasoning and SQL)
    Tool fallbacks: None (schema work is pure code generation)
    """

    PREFERRED_MODEL = ModelType.CLAUDE_OPUS

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute database design/optimization task."""

        self.logger.info(f"Executing database task: {task.description}")

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
        """Build prompt for database task."""

        db_engine = task.context.get("db_engine", "postgresql")
        migration_tool = task.context.get("migration_tool", "alembic")
        operation = task.context.get("operation", "design")  # design | migrate | optimize | seed
        existing_schema = task.context.get("existing_schema", "")
        query_patterns = task.context.get("query_patterns", [])
        scale = task.context.get("scale", "startup")  # startup | growth | enterprise

        return f"""
You are a senior database architect and DBA with deep expertise in {db_engine}.

Task: {task.description}

Context:
{task.context}

Database Engine: {db_engine}
Migration Tool: {migration_tool}
Operation: {operation}
Scale Target: {scale}
Existing Schema: {existing_schema or "None (greenfield)"}
Query Patterns: {query_patterns}

Anti-patterns to avoid:
{chr(10).join(f"- {p}" for p in SCHEMA_ANTIPATTERNS)}

Provide a complete database implementation covering:
1. Schema definition (CREATE TABLE / collection schema / document schema)
2. Migration scripts (up + down migrations)
3. Index strategy with justification for each index
4. Query optimization recommendations (EXPLAIN ANALYZE output interpretation)
5. Connection pool configuration
6. Seed data / fixtures for development
7. Performance considerations at {scale} scale

For each design decision, explain the trade-off (e.g., normalization vs. read performance).

Return JSON format:
{{
    "files": [
        {{
            "path": "migrations/001_initial_schema.sql",
            "content": "...",
            "change_type": "create"
        }},
        {{
            "path": "migrations/alembic/versions/001_initial.py",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "schema": {{
        "tables": [
            {{
                "name": "users",
                "columns": [...],
                "primary_key": "id",
                "foreign_keys": [...],
                "indexes": [...],
                "constraints": [...]
            }}
        ],
        "engine": "{db_engine}",
        "normalization_form": "3NF"
    }},
    "indexes": [
        {{
            "table": "users",
            "columns": ["email"],
            "type": "btree",
            "unique": true,
            "justification": "Frequent lookup by email during login"
        }}
    ],
    "query_optimizations": [
        {{
            "query": "SELECT ...",
            "issue": "Sequential scan on large table",
            "recommendation": "Add composite index on (status, created_at)",
            "estimated_improvement": "10x"
        }}
    ],
    "connection_pool": {{
        "min_connections": 5,
        "max_connections": 20,
        "timeout_seconds": 30,
        "recommendation": "..."
    }},
    "seed_data": [...],
    "anti_patterns_found": [],
    "design_decisions": [
        {{
            "decision": "...",
            "trade_off": "...",
            "chosen_approach": "..."
        }}
    ]
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate database output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Must have schema definition
        if not output.get("schema"):
            self.logger.warning("Output missing 'schema' definition")
            return False

        # Check tables have primary keys
        for table in output.get("schema", {}).get("tables", []):
            if not table.get("primary_key"):
                self.logger.warning(f"Table '{table.get('name')}' missing primary key")
                return False

        # Flag anti-patterns found
        anti_patterns = output.get("anti_patterns_found", [])
        if anti_patterns:
            self.logger.warning(f"Schema anti-patterns detected: {anti_patterns}")

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on schema completeness and best practices."""

        score = 0.35

        schema = output.get("schema", {})
        tables = schema.get("tables", [])

        if tables:
            # Reward tables with indexes
            tables_with_indexes = sum(1 for t in tables if t.get("indexes"))
            score += 0.1 * (tables_with_indexes / max(len(tables), 1))

            # Reward foreign key constraints
            tables_with_fks = sum(1 for t in tables if t.get("foreign_keys"))
            score += 0.05 * (tables_with_fks / max(len(tables), 1))

        if output.get("indexes"):
            score += 0.1
        if output.get("query_optimizations"):
            score += 0.1
        if output.get("connection_pool"):
            score += 0.1
        if output.get("design_decisions"):
            score += 0.1
        if not output.get("anti_patterns_found"):
            score += 0.1  # Bonus for clean schema
        if output.get("seed_data"):
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

    def get_anti_patterns(self, output: dict) -> list:
        """Return list of detected schema anti-patterns."""
        return output.get("anti_patterns_found", [])

    async def propose_alternative(self, task: Task) -> dict:
        """Propose event-sourcing / CQRS alternative for complex domains."""

        return {
            "agent": self.agent_type.value,
            "proposal": "event_sourcing_cqrs",
            "reasoning": (
                "For complex domains with audit requirements, use Event Sourcing + CQRS. "
                "Append-only event log provides full audit trail, enables temporal queries, "
                "and separates read/write models for independent scaling."
            ),
            "risk_score": 0.4,
            "complexity_score": 0.7,
            "estimated_time_hours": 20.0,
            "dependencies": ["postgresql", "alembic", "sqlalchemy"],
        }


# Register agent
register_agent(AgentType.DATABASE, DatabaseAgent)
