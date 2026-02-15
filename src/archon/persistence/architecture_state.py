"""
Architecture State stub.
"""

from typing import Dict


class ArchitectureState:
    def __init__(self, path: str):
        self.path = path

    async def initialize(self):
        pass

    async def apply_changes(self, changes: Dict):
        pass
