"""
Data Agent - handles data pipelines, ML model integration, feature engineering, and analytics.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# Supported pipeline frameworks
PIPELINE_FRAMEWORKS = [
    "apache_airflow",
    "prefect",
    "dagster",
    "luigi",
    "apache_spark",
    "dbt",
    "pandas",
    "polars",
]

# ML serving frameworks
ML_SERVING_FRAMEWORKS = [
    "fastapi",
    "torchserve",
    "triton",
    "bentoml",
    "mlflow",
    "seldon",
    "ray_serve",
]

# Data quality dimensions
DATA_QUALITY_DIMENSIONS = [
    "completeness",  # No missing values where required
    "accuracy",  # Values match real-world facts
    "consistency",  # No contradictions across datasets
    "timeliness",  # Data is up-to-date
    "uniqueness",  # No duplicates
    "validity",  # Values conform to defined formats/ranges
]


class DataAgent(BaseAgent):
    """
    Data agent handles:
    - ETL/ELT pipeline design and implementation (Airflow, Prefect, Dagster)
    - Data transformation and cleaning (pandas, polars, dbt)
    - Feature engineering for ML models
    - ML model serving API wrappers (FastAPI + model loading)
    - Data validation schemas (Great Expectations, Pandera)
    - Analytics query generation (SQL, BigQuery, Snowflake)
    - Data lineage documentation
    - Streaming data pipelines (Kafka consumers, Flink jobs)
    - Data warehouse schema design (star/snowflake schema)

    Primary model: Gemini Pro (1M context for analyzing large datasets/schemas)
    Tool fallbacks: None (pipeline code is generated)
    """

    PREFERRED_MODEL = ModelType.GEMINI_PRO

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute data engineering / ML task."""

        self.logger.info(f"Executing data task: {task.description}")

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
        """Build prompt for data/ML task."""

        operation = task.context.get(
            "operation", "pipeline"
        )  # pipeline | feature_eng | ml_serve | analytics | validate
        pipeline_framework = task.context.get("pipeline_framework", "prefect")
        data_sources = task.context.get("data_sources", [])
        data_sinks = task.context.get("data_sinks", [])
        ml_model_type = task.context.get("ml_model_type", "")
        schedule = task.context.get("schedule", "daily")
        data_volume = task.context.get(
            "data_volume", "medium"
        )  # small | medium | large | streaming

        return f"""
You are a senior data engineer and ML engineer with expertise in production data systems.

Task: {task.description}

Context:
{task.context}

Operation: {operation}
Pipeline Framework: {pipeline_framework}
Data Sources: {data_sources}
Data Sinks: {data_sinks}
ML Model Type: {ml_model_type or "N/A"}
Schedule: {schedule}
Data Volume: {data_volume}

Data quality dimensions to address:
{chr(10).join(f"- {dim}" for dim in DATA_QUALITY_DIMENSIONS)}

Provide a complete data engineering implementation covering:
1. Pipeline DAG definition (tasks, dependencies, schedule)
2. Data transformation logic (cleaning, normalization, enrichment)
3. Feature engineering (if ML task)
4. Data validation schema (Great Expectations / Pandera)
5. ML model serving endpoint (if applicable)
6. Analytics queries (SQL / BigQuery / Snowflake)
7. Data lineage documentation
8. Error handling and retry logic
9. Monitoring (data freshness, row count checks, schema drift alerts)

Best practices:
- Idempotent pipeline steps (safe to re-run)
- Incremental processing where possible (avoid full reloads)
- Schema evolution handling
- PII detection and masking
- Data quality checks at each stage

Return JSON format:
{{
    "files": [
        {{
            "path": "pipelines/user_events_pipeline.py",
            "content": "...",
            "change_type": "create"
        }}
    ],
    "pipeline": {{
        "name": "...",
        "framework": "{pipeline_framework}",
        "schedule": "{schedule}",
        "tasks": [
            {{
                "name": "extract",
                "type": "extract",
                "source": "...",
                "dependencies": []
            }}
        ],
        "estimated_runtime_minutes": 0
    }},
    "data_quality": {{
        "framework": "great_expectations",
        "expectations": [
            {{
                "column": "user_id",
                "expectation": "expect_column_values_to_not_be_null",
                "dimension": "completeness"
            }}
        ]
    }},
    "ml_serving": null,
    "analytics_queries": [
        {{
            "name": "daily_active_users",
            "sql": "...",
            "description": "..."
        }}
    ],
    "data_lineage": {{
        "sources": [],
        "transformations": [],
        "sinks": []
    }},
    "monitoring": {{
        "freshness_sla_hours": 24,
        "row_count_threshold_pct": 0.1,
        "schema_drift_alert": true
    }},
    "pii_fields": [],
    "estimated_daily_rows": 0
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate data pipeline output."""

        if "files" not in output:
            self.logger.warning("Output missing 'files' field")
            return False

        for file in output.get("files", []):
            if not all(k in file for k in ["path", "content", "change_type"]):
                self.logger.warning(f"File missing required fields: {file}")
                return False

        # Must have pipeline definition
        if not output.get("pipeline"):
            self.logger.warning("Output missing 'pipeline' definition")
            return False

        pipeline = output["pipeline"]
        if not pipeline.get("tasks"):
            self.logger.warning("Pipeline has no tasks defined")
            return False

        # Warn if no data quality checks
        if not output.get("data_quality", {}).get("expectations"):
            self.logger.warning("No data quality expectations defined — data reliability risk")

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on pipeline completeness."""

        score = 0.35

        pipeline = output.get("pipeline", {})
        tasks = pipeline.get("tasks", [])

        if tasks:
            score += 0.1

        dq = output.get("data_quality", {})
        expectations = dq.get("expectations", [])
        if expectations:
            # Reward coverage across quality dimensions
            covered_dims = set(e.get("dimension") for e in expectations if e.get("dimension"))
            score += 0.1 * (len(covered_dims) / len(DATA_QUALITY_DIMENSIONS))

        if output.get("analytics_queries"):
            score += 0.1
        if output.get("data_lineage", {}).get("transformations"):
            score += 0.1
        if output.get("monitoring"):
            score += 0.1
        if output.get("ml_serving"):
            score += 0.1
        if output.get("pii_fields") is not None:
            score += 0.05  # Reward PII awareness

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
        """Propose streaming-first data architecture."""

        return {
            "agent": self.agent_type.value,
            "proposal": "streaming_first_with_lambda_architecture",
            "reasoning": (
                "Use Lambda Architecture: streaming layer (Kafka + Flink) for real-time "
                "insights and batch layer (Spark/dbt) for historical accuracy. "
                "Enables both real-time dashboards and reliable historical reporting."
            ),
            "risk_score": 0.35,
            "complexity_score": 0.65,
            "estimated_time_hours": 24.0,
            "dependencies": ["apache-kafka", "apache-flink", "dbt", "great-expectations"],
        }


# Register agent
register_agent(AgentType.DATA, DataAgent)
