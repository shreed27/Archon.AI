"""
Task Graph stub.
"""

from typing import List
from archon.utils.schemas import Task


class TaskGraph:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self):
        pass

    async def store_tasks(self, tasks: List[Task]):
        pass
