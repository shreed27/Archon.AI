"""
ARCHON - Autonomous Engineering Organization CLI

A production-grade, distributed, multi-agent AI engineering operating system.
"""

__version__ = "0.1.0"
__author__ = "Archon Team"

from archon.manager.orchestrator import ManagerOrchestrator
from archon.agents.base_agent import BaseAgent
from archon.models.model_interface import ModelInterface

__all__ = ["ManagerOrchestrator", "BaseAgent", "ModelInterface"]
