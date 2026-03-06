"""
Base Agent class - abstract interface for all specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from archon.utils.schemas import Task, TaskResult, AgentType
from archon.manager.model_router import ModelType
from archon.models.model_router import ModelRouter
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all ARCHON agents.

    Each agent:
    - Receives structured tasks
    - Uses model assigned by Manager
    - Can propose tool usage
    - Can propose architectural alternatives
    - Returns structured JSON output
    - Is performance scored
    """

    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.logger = get_logger(f"agent.{agent_type.value}")
        self.model_router = ModelRouter()

    @abstractmethod
    async def execute(self, task: Task, model: ModelType, project_memory=None) -> TaskResult:
        """
        Execute task using assigned model.

        Args:
            task: Task to execute
            model: AI model to use

        Returns:
            TaskResult with output and metadata
        """
        pass

    @abstractmethod
    async def validate_output(self, output: Dict[str, Any]) -> bool:
        """
        Validate agent output meets quality standards.

        Args:
            output: Agent output to validate

        Returns:
            True if valid, False otherwise
        """
        pass

    async def propose_alternative(self, task: Task) -> Dict[str, Any]:
        """
        Propose alternative approach to task.

        Used during deliberation when agent disagrees with current approach.

        Returns:
            Proposal dict with reasoning
        """
        return {
            "agent": self.agent_type.value,
            "proposal": "default_approach",
            "reasoning": "No alternative proposed",
            "risk_score": 0.5,
            "complexity_score": 0.5,
            "estimated_time_hours": 1.0,
        }

    async def _call_model(self, model: Any, messages: Any) -> Dict[str, Any]:
        """
        Call AI model using the unified ModelRouter.
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        response_text = await self.model_router.generate(messages)

        # Try to parse as JSON if it looks like JSON
        import json

        try:
            start = response_text.find("{")
            end = response_text.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(response_text[start : end + 1])
                return {"parsed_json": parsed, "content": response_text}
        except Exception:
            pass

        return {"content": response_text, "parsed_json": {}}


# Agent registry
_AGENTS = {}


def register_agent(agent_type: AgentType, agent_class: type):
    """Register agent class for agent type."""
    _AGENTS[agent_type] = agent_class


def get_agent(agent_type: AgentType) -> BaseAgent:
    """Get agent instance for agent type."""

    if isinstance(agent_type, str):
        agent_type = AgentType.from_str(agent_type)

    if agent_type not in _AGENTS:
        raise ValueError(f"No agent registered for type: {agent_type}")

    return _AGENTS[agent_type](agent_type)
