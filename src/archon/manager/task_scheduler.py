"""
Task Scheduler stub.
"""

from typing import Dict, List
from archon.utils.schemas import Task


class TaskScheduler:
    async def create_task_dag(self, spec: Dict) -> List[Task]:
        return []

    async def get_executable_tasks(self, tasks: List[Task]) -> List[Task]:
        return []
