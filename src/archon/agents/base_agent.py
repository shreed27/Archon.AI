"""
Base Agent class - abstract interface for all specialized agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from archon.utils.schemas import Task, TaskResult, AgentType
from archon.manager.model_router import ModelType
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

    @abstractmethod
    async def execute(self, task: Task, model: ModelType) -> TaskResult:
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

    async def _call_model(self, model: ModelType, prompt: str) -> Dict[str, Any]:
        """
        Call AI model with prompt.

        Routes to appropriate model client based on ModelType.
        """

        if model in [ModelType.GPT4, ModelType.GPT4_TURBO]:
            from archon.models.openai_client import OpenAIClient

            client = OpenAIClient()
            return await client.complete(prompt, model.value)

        elif model in [ModelType.CLAUDE_OPUS, ModelType.CLAUDE_SONNET]:
            from archon.models.anthropic_client import AnthropicClient

            client = AnthropicClient()
            return await client.complete(prompt, model.value)

        elif model in [ModelType.GEMINI_PRO, ModelType.GEMINI_FLASH]:
            from archon.models.google_client import GoogleClient

            client = GoogleClient()
            return await client.complete(prompt, model.value)

        else:
            raise ValueError(f"Unknown model type: {model}")


# Agent registry
_AGENTS = {}


def register_agent(agent_type: AgentType, agent_class: type):
    """Register agent class for agent type."""
    _AGENTS[agent_type] = agent_class


def get_agent(agent_type: AgentType) -> BaseAgent:
    """Get agent instance for agent type."""

    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)

    if agent_type not in _AGENTS:
        raise ValueError(f"No agent registered for type: {agent_type}")

    return _AGENTS[agent_type](agent_type)
