"""
Performance Agent - handles profiling, optimization, caching, and load testing.
"""

from datetime import datetime
from archon.agents.base_agent import BaseAgent, register_agent
from archon.utils.schemas import Task, TaskResult, AgentType, FileChange
from archon.manager.model_router import ModelType


# Performance categories
PERF_CATEGORIES = [
    "cpu_bound",  # Algorithmic complexity, tight loops
    "memory_bound",  # Memory leaks, excessive allocation
    "io_bound",  # Disk I/O, network latency
    "db_bound",  # N+1 queries, missing indexes
    "cache_miss",  # Cache invalidation, cold starts
    "concurrency",  # Lock contention, thread starvation
    "serialization",  # JSON/protobuf overhead
    "network",  # Payload size, round trips, CDN
]

# Big-O complexity ratings
COMPLEXITY_RATINGS = {
    "O(1)": 1.0,
    "O(log n)": 0.9,
    "O(n)": 0.7,
    "O(n log n)": 0.5,
    "O(n²)": 0.2,
    "O(2^n)": 0.0,
}


class PerformanceAgent(BaseAgent):
    """
    Performance agent handles:
    - CPU/memory/I/O profiling analysis (cProfile, py-spy, memory_profiler)
    - Algorithmic complexity analysis (Big-O identification)
    - Database query optimization (N+1 detection, query plan analysis)
    - Caching strategy design (Redis, Memcached, in-process LRU)
    - Cache invalidation patterns
    - Load testing scripts (Locust, k6, Artillery)
    - Async/concurrent code optimization
    - Bundle size analysis (webpack-bundle-analyzer)
    - API response time optimization
    - CDN and edge caching configuration

    Primary model: Gemini Pro (1M context for analyzing large codebases)
    Tool fallbacks: None (analysis is AI-driven; load test scripts are generated)
    """

    PREFERRED_MODEL = ModelType.GEMINI_PRO

    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        """Execute performance analysis/optimization task."""

        self.logger.info(f"Executing performance task: {task.description}")

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
        """Build prompt for performance task."""

        operation = task.context.get(
            "operation", "analyze"
        )  # analyze | optimize | load_test | cache
        target_p99_ms = task.context.get("target_p99_ms", 200)
        target_rps = task.context.get("target_rps", 1000)
        profile_data = task.context.get("profile_data", "")
        source_files = task.context.get("source_files", [])
        stack = task.context.get("stack", "Python/FastAPI/PostgreSQL")

        return f"""
You are a senior performance engineer and SRE with expertise in profiling and optimization.

Task: {task.description}

Context:
{task.context}

Operation: {operation}
Stack: {stack}
Performance Targets: p99 < {target_p99_ms}ms, {target_rps} RPS
Profile Data: {profile_data or "Not provided — analyze from source code"}
Source Files: {source_files}

Performance categories to analyze:
{chr(10).join(f"- {cat}" for cat in PERF_CATEGORIES)}

Provide a complete performance analysis and optimization plan:
1. Bottleneck identification (with category, severity, and estimated impact)
2. Algorithmic complexity analysis (Big-O for critical paths)
3. N+1 query detection and fixes
4. Caching strategy (what to cache, TTL, invalidation strategy, cache key design)
5. Optimized code implementations (with before/after comparison)
6. Load test script (Locust/k6) targeting {target_rps} RPS
7. Monitoring/alerting recommendations (p50/p95/p99 thresholds)
8. Quick wins vs. long-term improvements

Return JSON format:
{{
    "bottlenecks": [
        {{
            "id": "PERF-001",
            "category": "db_bound",
            "severity": "critical",
            "location": "src/api/users.py:get_users()",
            "description": "N+1 query: fetching user roles in a loop",
            "estimated_impact": "50x slower than necessary",
            "complexity_before": "O(n)",
            "complexity_after": "O(1)",
            "fix": "Use JOIN or prefetch_related"
        }}
    ],
    "files": [
        {{
            "path": "src/api/users.py",
            "content": "...",
            "change_type": "modify"
        }}
    ],
    "caching_strategy": {{
        "backend": "redis",
        "entries": [
            {{
                "key_pattern": "user:{{user_id}}:profile",
                "ttl_seconds": 300,
                "invalidation_triggers": ["user.updated", "user.deleted"],
                "estimated_hit_rate": 0.85
            }}
        ]
    }},
    "load_test": {{
        "tool": "locust",
        "file_path": "tests/load/locustfile.py",
        "content": "...",
        "scenarios": [...]
    }},
    "monitoring": {{
        "metrics": ["p50_ms", "p95_ms", "p99_ms", "error_rate", "rps"],
        "alert_thresholds": {{
            "p99_ms": {target_p99_ms},
            "error_rate": 0.01
        }}
    }},
    "quick_wins": [...],
    "long_term_improvements": [...],
    "estimated_improvement": {{
        "latency_reduction_pct": 0,
        "throughput_increase_pct": 0
    }}
}}
"""

    async def validate_output(self, output: dict) -> bool:
        """Validate performance output."""

        if "bottlenecks" not in output:
            self.logger.warning("Output missing 'bottlenecks' field")
            return False

        required_bottleneck_fields = ["id", "category", "severity", "description", "fix"]
        for b in output.get("bottlenecks", []):
            if not all(k in b for k in required_bottleneck_fields):
                self.logger.warning(f"Bottleneck missing required fields: {b.get('id', 'unknown')}")
                return False

            if b.get("category") not in PERF_CATEGORIES:
                self.logger.warning(f"Unknown performance category: {b.get('category')}")
                return False

        return True

    def _compute_quality_score(self, output: dict) -> float:
        """Compute quality score based on analysis depth."""

        score = 0.35

        bottlenecks = output.get("bottlenecks", [])
        if bottlenecks:
            # Reward complexity analysis
            with_complexity = sum(1 for b in bottlenecks if b.get("complexity_before"))
            score += 0.1 * (with_complexity / max(len(bottlenecks), 1))

        if output.get("files"):
            score += 0.1
        if output.get("caching_strategy", {}).get("entries"):
            score += 0.15
        if output.get("load_test", {}).get("content"):
            score += 0.15
        if output.get("monitoring"):
            score += 0.1
        if output.get("quick_wins"):
            score += 0.05
        if output.get("estimated_improvement"):
            score += 0.1

        return min(score, 1.0)

    def _extract_file_changes(self, output: dict) -> list:
        """Extract file changes (optimized code + load test) from output."""

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

        # Also include load test file
        load_test = output.get("load_test", {})
        if load_test.get("file_path") and load_test.get("content"):
            changes.append(
                FileChange(
                    path=load_test["file_path"],
                    change_type="create",
                    lines_added=len(load_test["content"].split("\n")),
                    lines_removed=0,
                    agent=self.agent_type.value,
                )
            )

        return changes

    def get_critical_bottlenecks(self, output: dict) -> list:
        """Return only critical severity bottlenecks."""
        return [b for b in output.get("bottlenecks", []) if b.get("severity") == "critical"]

    async def propose_alternative(self, task: Task) -> dict:
        """Propose async-first architecture for performance."""

        return {
            "agent": self.agent_type.value,
            "proposal": "async_first_with_caching_layer",
            "reasoning": (
                "Rewrite synchronous hot paths as async, add Redis caching layer "
                "for frequently-read data, and implement connection pooling. "
                "Expected 5-10x throughput improvement with minimal code changes."
            ),
            "risk_score": 0.25,
            "complexity_score": 0.45,
            "estimated_time_hours": 12.0,
            "dependencies": ["redis", "asyncio", "aiohttp", "locust"],
        }


# Register agent
register_agent(AgentType.PERFORMANCE, PerformanceAgent)
