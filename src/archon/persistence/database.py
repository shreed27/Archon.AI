"""
Database - SQLite persistence for tasks, decisions, and metrics.
"""

import aiosqlite
from typing import Dict, Optional, Any, List
from pathlib import Path
from datetime import datetime
import json

from archon.utils.schemas import TaskStatus, Task, TaskResult, Decision


class Database:
    """
    SQLite database for persisting ARCHON state.
    Stores tasks, decisions, metrics, and file ownership.
    """

    def __init__(self, path: str):
        self.path = path
        self.db: Optional[aiosqlite.Connection] = None

    async def initialize(self):
        """Initialize database and create tables."""
        db_path = Path(self.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db = await aiosqlite.connect(self.path)
        await self._create_tables()

    async def _create_tables(self):
        """Create database schema."""
        if not self.db:
            return

        # Tasks table
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                model_assigned TEXT,
                tool_assigned TEXT,
                status TEXT NOT NULL,
                dependencies TEXT,
                quality_threshold REAL,
                context TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """
        )

        # Task results table
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS task_results (
                task_id TEXT PRIMARY KEY,
                success INTEGER NOT NULL,
                output TEXT,
                quality_score REAL,
                execution_time_ms INTEGER,
                model_used TEXT,
                tool_used TEXT,
                error TEXT,
                timestamp TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """
        )

        # Decisions table
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                conflict_id TEXT PRIMARY KEY,
                chosen_agent TEXT NOT NULL,
                chosen_proposal TEXT NOT NULL,
                reasoning TEXT,
                timestamp TEXT
            )
        """
        )

        # Tool usage log
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                execution_time_ms INTEGER,
                timestamp TEXT
            )
        """
        )

        # File ownership tracking
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS file_ownership (
                path TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                last_modified TEXT NOT NULL
            )
        """
        )

        # Project specifications
        await self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS specifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                components TEXT,
                architecture TEXT,
                created_at TEXT
            )
        """
        )

        await self.db.commit()

    async def store_specification(self, spec: Dict):
        """Store project specification."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT INTO specifications (goal, components, architecture, created_at)
            VALUES (?, ?, ?, ?)
        """,
            (
                spec.get("goal", ""),
                json.dumps(spec.get("components", [])),
                json.dumps(spec.get("architecture", {})),
                datetime.now().isoformat(),
            ),
        )
        await self.db.commit()

    async def store_task(self, task: Task):
        """Store a task."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT OR REPLACE INTO tasks 
            (task_id, description, agent_type, model_assigned, tool_assigned, 
             status, dependencies, quality_threshold, context, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task.task_id,
                task.description,
                task.agent_type.value,
                task.model_assigned,
                task.tool_assigned,
                task.status.value,
                json.dumps(task.dependencies),
                task.quality_threshold,
                json.dumps(task.context),
                task.created_at.isoformat(),
                task.completed_at.isoformat() if task.completed_at else None,
            ),
        )
        await self.db.commit()

    async def update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status."""
        if not self.db:
            return

        completed_at = datetime.now().isoformat() if status == TaskStatus.COMPLETED else None

        await self.db.execute(
            """
            UPDATE tasks 
            SET status = ?, completed_at = ?
            WHERE task_id = ?
        """,
            (status.value, completed_at, task_id),
        )
        await self.db.commit()

    async def store_task_result(self, result: TaskResult):
        """Store task execution result."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT OR REPLACE INTO task_results
            (task_id, success, output, quality_score, execution_time_ms,
             model_used, tool_used, error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.task_id,
                1 if result.success else 0,
                json.dumps(result.output),
                result.quality_score,
                result.execution_time_ms,
                result.model_used,
                result.tool_used,
                result.error,
                datetime.now().isoformat(),
            ),
        )
        await self.db.commit()

    async def store_decision(self, decision: Decision):
        """Store arbitration decision."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT INTO decisions
            (conflict_id, chosen_agent, chosen_proposal, reasoning, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                decision.conflict_id,
                decision.chosen_agent,
                decision.chosen_proposal,
                decision.reasoning,
                decision.timestamp.isoformat(),
            ),
        )
        await self.db.commit()

    async def log_tool_usage(self, log: Dict):
        """Log external tool usage."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT INTO tool_usage
            (task_id, tool_name, success, execution_time_ms, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                log.get("task_id"),
                log.get("tool_name"),
                1 if log.get("success") else 0,
                log.get("execution_time_ms"),
                datetime.now().isoformat(),
            ),
        )
        await self.db.commit()

    async def update_file_ownership(self, path: str, agent: str, timestamp: Any):
        """Update file ownership tracking."""
        if not self.db:
            return

        await self.db.execute(
            """
            INSERT OR REPLACE INTO file_ownership
            (path, agent, last_modified)
            VALUES (?, ?, ?)
        """,
            (
                path,
                agent,
                timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
            ),
        )
        await self.db.commit()

    async def count_tasks(self) -> int:
        """Count total tasks."""
        if not self.db:
            return 0

        async with self.db.execute("SELECT COUNT(*) FROM tasks") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def count_tasks_by_status(self, status: TaskStatus) -> int:
        """Count tasks by status."""
        if not self.db:
            return 0

        async with self.db.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = ?", (status.value,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_active_tasks(self) -> List[Dict]:
        """Get all active (non-completed) tasks."""
        if not self.db:
            return []

        async with self.db.execute(
            """
            SELECT task_id, description, agent_type, status, created_at
            FROM tasks
            WHERE status != ?
            ORDER BY created_at DESC
        """,
            (TaskStatus.COMPLETED.value,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "task_id": row[0],
                    "description": row[1],
                    "agent_type": row[2],
                    "status": row[3],
                    "created_at": row[4],
                }
                for row in rows
            ]

    async def get_agent_metrics(self) -> Dict:
        """Get aggregated agent metrics."""
        if not self.db:
            return {}

        async with self.db.execute(
            """
            SELECT 
                t.agent_type,
                COUNT(*) as total,
                SUM(CASE WHEN tr.success = 1 THEN 1 ELSE 0 END) as successful,
                AVG(tr.quality_score) as avg_quality,
                AVG(tr.execution_time_ms) as avg_time
            FROM tasks t
            LEFT JOIN task_results tr ON t.task_id = tr.task_id
            WHERE tr.task_id IS NOT NULL
            GROUP BY t.agent_type
        """
        ) as cursor:
            rows = await cursor.fetchall()
            return {
                row[0]: {
                    "total": row[1],
                    "successful": row[2],
                    "avg_quality": row[3],
                    "avg_time_ms": row[4],
                    "success_rate": row[2] / row[1] if row[1] > 0 else 0,
                }
                for row in rows
            }

    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
