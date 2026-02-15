"""
Model Interface stub.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class ModelInterface(ABC):
    @abstractmethod
    async def complete(self, prompt: str, model: str) -> Dict[str, Any]:
        pass
