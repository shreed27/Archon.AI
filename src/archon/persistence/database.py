"""
Database stub.
"""

from typing import Dict, Optional, Any
from archon.utils.schemas import TaskStatus


class Database:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self):
        pass

    async def store_specification(self, spec: Dict):
        pass

    async def update_task_status(self, task_id: str, status: TaskStatus):
        pass

    async def log_tool_usage(self, log: Dict):
        pass

    async def update_file_ownership(self, path: str, agent: str, timestamp: Any):
        pass

    async def count_tasks(self) -> int:
        return 0

    async def count_tasks_by_status(self, status: TaskStatus) -> int:
        return 0

    async def get_active_tasks(self) -> list:
        return []

    async def get_agent_metrics(self) -> dict:
        return {}
