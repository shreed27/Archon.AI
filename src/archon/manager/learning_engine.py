"""
Learning Engine stub.
"""

from pathlib import Path
from archon.utils.schemas import Task, TaskResult


class LearningEngine:
    async def initialize(self, archon_dir: Path):
        pass

    async def record_outcome(self, task: Task, result: TaskResult):
        pass
