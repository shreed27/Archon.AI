"""
Task Scheduler - DAG construction and dependency resolution.
"""

from typing import Dict, List, Set
from collections import defaultdict, deque
import uuid
from datetime import datetime

from archon.utils.schemas import Task, TaskStatus, AgentType


class TaskScheduler:
    """
    Constructs task DAG and determines execution order.
    Uses topological sorting for dependency resolution.
    """

    def __init__(self):
        self.task_graph: Dict[str, List[str]] = defaultdict(list)  # task_id -> dependencies
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)  # task_id -> dependents

    async def create_task_dag(self, spec: Dict) -> List[Task]:
        """
        Parse project specification and create task DAG.

        Args:
            spec: Project specification with tasks and dependencies

        Returns:
            List of Task objects with dependencies resolved
        """
        tasks = []
        task_map = {}

        # First pass: Create all tasks
        for task_def in spec.get("tasks", []):
            task_id = task_def.get("id", f"task_{uuid.uuid4().hex[:8]}")

            task = Task(
                task_id=task_id,
                description=task_def["description"],
                agent_type=AgentType(task_def.get("agent", "backend")),
                dependencies=task_def.get("dependencies", []),
                quality_threshold=task_def.get("quality_threshold", 0.8),
                context=task_def.get("context", {}),
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
            )

            tasks.append(task)
            task_map[task_id] = task

        # Second pass: Build dependency graph
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    self.task_graph[task.task_id].append(dep_id)
                    self.reverse_graph[dep_id].append(task.task_id)

        # Validate DAG (no cycles)
        if self._has_cycle(tasks):
            raise ValueError("Task dependencies contain a cycle")

        return tasks

    async def get_executable_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Get tasks that can be executed now (all dependencies completed).

        Args:
            tasks: List of all tasks

        Returns:
            List of tasks ready for execution
        """
        executable = []
        completed_ids = {t.task_id for t in tasks if t.status == TaskStatus.COMPLETED}

        for task in tasks:
            if task.status == TaskStatus.PENDING:
                # Check if all dependencies are completed
                deps_met = all(dep_id in completed_ids for dep_id in task.dependencies)
                if deps_met:
                    executable.append(task)

        return executable

    async def get_execution_order(self, tasks: List[Task]) -> List[List[str]]:
        """
        Get execution order as levels (tasks in same level can run in parallel).

        Returns:
            List of levels, where each level is a list of task IDs
        """
        # Build in-degree map
        in_degree = {task.task_id: len(task.dependencies) for task in tasks}

        # Find tasks with no dependencies
        queue = deque([task.task_id for task in tasks if len(task.dependencies) == 0])

        levels = []

        while queue:
            # All tasks in current level can execute in parallel
            current_level = list(queue)
            levels.append(current_level)

            # Process current level
            next_queue = []
            for task_id in current_level:
                # Reduce in-degree for dependent tasks
                for dependent_id in self.reverse_graph.get(task_id, []):
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        next_queue.append(dependent_id)

            queue = deque(next_queue)

        return levels

    def _has_cycle(self, tasks: List[Task]) -> bool:
        """Check if task graph has cycles using DFS."""
        visited = set()
        rec_stack = set()

        def dfs(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            for dep_id in self.task_graph.get(task_id, []):
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task in tasks:
            if task.task_id not in visited:
                if dfs(task.task_id):
                    return True

        return False

    async def estimate_completion_time(self, tasks: List[Task]) -> float:
        """
        Estimate total completion time considering parallelization.

        Returns:
            Estimated hours to completion
        """
        levels = await self.get_execution_order(tasks)
        total_time = 0.0

        for level in levels:
            # Max time in this level (parallel execution)
            level_time = max(
                task.context.get("estimated_time_hours", 1.0)
                for task in tasks
                if task.task_id in level
            )
            total_time += level_time

        return total_time
