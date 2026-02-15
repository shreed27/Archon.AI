"""
Arbitrator stub.
"""

from typing import Dict
from archon.utils.schemas import Task, TaskResult, Conflict


class Arbitrator:
    async def resolve_conflict(self, task: Task, result: TaskResult) -> Dict:
        return {}
