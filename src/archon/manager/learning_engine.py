"""
Learning Engine - Cross-project learning and performance optimization.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib

try:
    import chromadb
    from chromadb.config import Settings

    CHROMA_AVAILABLE = True
except ImportError:
    chromadb = None
    CHROMA_AVAILABLE = False

from archon.utils.schemas import Task, TaskResult, AgentMetrics
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class LearningEngine:
    """
    Tracks performance across projects and improves routing decisions.
    Uses Vector Memory (ChromaDB) to find semantically similar past tasks and outcomes.
    """

    def __init__(self):
        self.archon_dir: Optional[Path] = None
        self.metrics_file: Optional[Path] = None
        self.outcomes_file: Optional[Path] = None
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.task_outcomes: List[Dict] = []

        # Vector DB
        self.chroma_client = None
        self.collection = None

    async def initialize(self, archon_dir: Path):
        """
        Initialize learning engine with project directory.

        Args:
            archon_dir: Path to .archon directory
        """
        self.archon_dir = archon_dir
        self.archon_dir.mkdir(parents=True, exist_ok=True)

        self.metrics_file = self.archon_dir / "agent_metrics.json"
        self.outcomes_file = self.archon_dir / "task_outcomes.json"

        # Initialize ChromaDB
        memory_dir = self.archon_dir / "memory"
        memory_dir.mkdir(exist_ok=True)

        if CHROMA_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(path=str(memory_dir))

                self.collection = self.chroma_client.get_or_create_collection(
                    name="task_history", metadata={"hnsw:space": "cosine"}
                )
                logger.info("Vector Memory (ChromaDB) initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Vector Memory: {e}")
                self.chroma_client = None
        else:
            logger.warning("ChromaDB not installed. Vector Memory disabled.")

        # Load existing data
        await self._load_metrics()
        await self._load_outcomes()

    async def record_outcome(self, task: Task, result: TaskResult):
        """
        Record task outcome for future learning.

        Args:
            task: The task that was executed
            result: The result of execution
        """
        outcome = {
            "task_id": task.task_id,
            "description": task.description,
            "description_hash": self._hash_description(task.description),
            "agent_type": task.agent_type.value,
            "model_used": result.model_used or "unknown",
            "tool_used": result.tool_used or "none",
            "success": result.success,
            "quality_score": result.quality_score,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": datetime.now().isoformat(),
            # Store a summary for embedding
            "context_summary": f"Task: {task.description}. Agent: {task.agent_type.value}. Success: {result.success}",
        }

        self.task_outcomes.append(outcome)
        await self._save_outcomes()

        # Update agent metrics
        await self._update_agent_metrics(task, result)

        # Add to Vector Memory
        if self.collection:
            try:
                self.collection.add(
                    documents=[outcome["context_summary"]],
                    metadatas=[
                        {
                            "task_id": task.task_id,
                            "agent_type": task.agent_type.value,
                            "success": str(result.success),
                            "quality_score": result.quality_score,
                            "model_used": outcome["model_used"],
                            "timestamp": outcome["timestamp"],
                        }
                    ],
                    ids=[task.task_id],
                )
            except Exception as e:
                logger.error(f"Failed to add memory to Vector DB: {e}")

    async def get_similar_tasks(self, task_description: str, limit: int = 5) -> List[Dict]:
        """
        Find similar tasks from history using Semantic Search.

        Args:
            task_description: Description of current task
            limit: Maximum number of similar tasks to return

        Returns:
            List of similar task outcomes
        """
        if not self.collection:
            return []

        try:
            results = self.collection.query(query_texts=[task_description], n_results=limit)

            # Retrieve full outcomes based on IDs
            similar_outcomes = []
            if results["ids"]:
                found_ids = results["ids"][0]
                # Map IDs back to full outcomes from JSON storage (faster than storing all in metadata)
                # Or just use metadata if sufficient

                # Let's verify metadata content
                metadatas = results["metadatas"][0]

                for i, task_id in enumerate(found_ids):
                    # Find full details from task_outcomes list
                    # Optimization: create a lookup dict if list is huge
                    match = next((o for o in self.task_outcomes if o["task_id"] == task_id), None)
                    if match:
                        similar_outcomes.append(match)

            return similar_outcomes

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def get_best_model_for_task(self, task: Task) -> Optional[str]:
        """
        Recommend best model based on semantically similar past tasks.
        """
        similar = await self.get_similar_tasks(task.description, limit=10)

        if not similar:
            return None

        # Find model with best average quality score in SIMILAR tasks
        model_scores: Dict[str, List[float]] = {}

        for outcome in similar:
            if outcome["model_used"] and outcome["success"]:
                model = outcome["model_used"]
                if model not in model_scores:
                    model_scores[model] = []
                model_scores[model].append(outcome["quality_score"])

        if not model_scores:
            return None

        # Calculate averages
        model_averages = {
            model: sum(scores) / len(scores) for model, scores in model_scores.items()
        }

        # Return best model
        best_model = max(model_averages.items(), key=lambda x: x[1])
        logger.info(
            f"Learning Engine recommends {best_model[0]} based on {len(similar)} similar tasks."
        )
        return best_model[0]

    async def get_agent_performance(self, agent_type: str) -> Optional[AgentMetrics]:
        """Get performance metrics for an agent."""
        return self.agent_metrics.get(agent_type)

    async def get_all_metrics(self) -> Dict[str, AgentMetrics]:
        """Get all agent metrics."""
        return self.agent_metrics

    async def should_use_tool(self, tool_name: str, task_type: str) -> bool:
        """
        Determine if a tool should be used based on historical performance.
        Checks similar tasks first.
        """
        # Try to find similar tasks that used this tool
        # 'task_type' is a string description here? Or enum?
        # If it's a description, we can semantic search.

        similar = await self.get_similar_tasks(task_type, limit=10)

        tool_outcomes = [o for o in similar if o.get("tool_used") == tool_name and o["success"]]

        ai_outcomes = [
            o for o in similar if o.get("model_used") and not o.get("tool_used") and o["success"]
        ]

        if not tool_outcomes and not ai_outcomes:
            # Fallback to global stats if no similar tasks found
            tool_outcomes = [
                o for o in self.task_outcomes if o.get("tool_used") == tool_name and o["success"]
            ]
            ai_outcomes = [
                o
                for o in self.task_outcomes
                if o.get("model_used") and not o.get("tool_used") and o["success"]
            ]

        if not tool_outcomes or not ai_outcomes:
            return False

        tool_avg = sum(o["quality_score"] for o in tool_outcomes) / len(tool_outcomes)
        ai_avg = sum(o["quality_score"] for o in ai_outcomes) / len(ai_outcomes)

        return tool_avg > ai_avg

    async def _update_agent_metrics(self, task: Task, result: TaskResult):
        """Update metrics for an agent."""
        agent_type = task.agent_type.value

        if agent_type not in self.agent_metrics:
            self.agent_metrics[agent_type] = AgentMetrics(
                agent_type=agent_type,
                tasks_completed=0,
                tasks_failed=0,
                avg_quality_score=0.0,
                avg_execution_time_ms=0,
                success_rate=0.0,
                last_updated=datetime.now(),
            )

        metrics = self.agent_metrics[agent_type]

        # Update counts
        if result.success:
            metrics.tasks_completed += 1
        else:
            metrics.tasks_failed += 1

        total_tasks = metrics.tasks_completed + metrics.tasks_failed

        # Update averages
        metrics.avg_quality_score = (
            metrics.avg_quality_score * (total_tasks - 1) + result.quality_score
        ) / total_tasks

        metrics.avg_execution_time_ms = int(
            (metrics.avg_execution_time_ms * (total_tasks - 1) + result.execution_time_ms)
            / total_tasks
        )

        metrics.success_rate = metrics.tasks_completed / total_tasks
        metrics.last_updated = datetime.now()

        await self._save_metrics()

    async def _load_metrics(self):
        """Load agent metrics from disk."""
        if self.metrics_file and self.metrics_file.exists():
            try:
                data = json.loads(self.metrics_file.read_text())
                for agent_type, metrics_dict in data.items():
                    metrics_dict["last_updated"] = datetime.fromisoformat(
                        metrics_dict["last_updated"]
                    )
                    self.agent_metrics[agent_type] = AgentMetrics(**metrics_dict)
            except Exception:
                pass

    async def _save_metrics(self):
        """Save agent metrics to disk."""
        if self.metrics_file:
            data = {
                agent_type: {
                    **metrics.model_dump(),
                    "last_updated": metrics.last_updated.isoformat(),
                }
                for agent_type, metrics in self.agent_metrics.items()
            }
            self.metrics_file.write_text(json.dumps(data, indent=2))

    async def _load_outcomes(self):
        """Load task outcomes from disk."""
        if self.outcomes_file and self.outcomes_file.exists():
            try:
                self.task_outcomes = json.loads(self.outcomes_file.read_text())
            except Exception:
                self.task_outcomes = []

    async def _save_outcomes(self):
        """Save task outcomes to disk."""
        if self.outcomes_file:
            self.outcomes_file.write_text(json.dumps(self.task_outcomes, indent=2))

    def _hash_description(self, description: str) -> str:
        """Create hash of task description for similarity matching."""
        normalized = description.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
