"""
Model Router - Selects optimal AI model for each task.

Routes tasks to GPT-4, Claude, or Gemini based on task characteristics.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

from archon.utils.schemas import Task
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class ModelType(Enum):
    """Available AI models."""

    # OpenAI
    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    O1 = "o1"
    O3_MINI = "o3-mini"

    # Anthropic
    CLAUDE_OPUS = "claude-3-opus-20240229"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_SONNET_4 = "claude-sonnet-4-5"
    CLAUDE_SONNET_4_THINKING = "claude-sonnet-4-5-thinking"
    CLAUDE_SONNET_46 = "claude-sonnet-4-6"
    CLAUDE_OPUS_46_THINKING = "claude-opus-4-6-thinking"

    # Google
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH = "gemini-2.0-flash-exp"
    GEMINI_25_PRO_HIGH = "gemini-2.5-pro-high"
    GEMINI_25_PRO_LOW = "gemini-2.5-pro-low"
    GEMINI_25_FLASH = "gemini-2.5-flash"

    # Open-source / other
    GPT_OSS_120B = "gpt-oss-120b-medium"


@dataclass
class ModelSelectionCriteria:
    """Criteria for model selection."""

    task_complexity: float  # 0.0 - 1.0
    reasoning_depth: float  # 0.0 - 1.0
    context_size: int  # tokens required
    speed_priority: float  # 0.0 - 1.0 (1.0 = fastest)
    cost_constraint: float  # max cost per task
    historical_performance: float  # learned metric


class ModelRouter:
    """
    Selects optimal AI model for each task.

    Selection based on:
    - Task characteristics (complexity, reasoning depth, context size)
    - Model capabilities (reasoning strength, context window, speed)
    - Historical performance (learned from past executions)
    - Cost constraints
    """

    # Model capability matrix
    MODEL_CAPABILITIES = {
        ModelType.GPT4_TURBO: {
            "max_context": 128_000,
            "reasoning_strength": 0.95,
            "speed_score": 0.7,
            "cost_per_1k_tokens": 0.01,
            "best_for": ["complex_logic", "architectural_decisions", "backend_logic"],
        },
        ModelType.CLAUDE_OPUS: {
            "max_context": 200_000,
            "reasoning_strength": 0.93,
            "speed_score": 0.5,
            "cost_per_1k_tokens": 0.015,
            "best_for": ["security_review", "large_refactors", "code_analysis"],
        },
        ModelType.CLAUDE_SONNET: {
            "max_context": 200_000,
            "reasoning_strength": 0.90,
            "speed_score": 0.8,
            "cost_per_1k_tokens": 0.003,
            "best_for": ["general_coding", "refactoring", "testing"],
        },
        ModelType.GEMINI_FLASH: {
            "max_context": 1_000_000,
            "reasoning_strength": 0.85,
            "speed_score": 0.95,
            "cost_per_1k_tokens": 0.0001,
            "best_for": ["frontend_ui", "fast_iteration", "documentation"],
        },
    }

    def __init__(self):
        self.historical_weights: Dict[str, Dict[ModelType, float]] = {}

    async def select_model(self, task: Task) -> ModelType:
        """
        Select optimal model using multi-criteria decision analysis.

        Algorithm:
        1. Extract task characteristics
        2. Score each model against criteria
        3. Apply historical performance weights
        4. Return highest-scoring model

        Args:
            task: Task to execute

        Returns:
            Selected ModelType
        """

        criteria = self._extract_criteria(task)
        scores = {}

        # Score each model
        for model, capabilities in self.MODEL_CAPABILITIES.items():
            score = self._calculate_model_score(model, capabilities, criteria)
            scores[model] = score

        # Apply historical performance weights
        if task.agent_type in self.historical_weights:
            for model in scores:
                historical_weight = self.historical_weights[task.agent_type].get(model, 1.0)
                scores[model] *= historical_weight

        # Select best model
        best_model = max(scores, key=scores.get)

        logger.info(
            f"Selected {best_model.value} for {task.agent_type} task "
            f"(score: {scores[best_model]:.2f})"
        )

        return best_model

    def _extract_criteria(self, task: Task) -> ModelSelectionCriteria:
        """
        Extract selection criteria from task.

        Uses heuristics and task metadata to determine:
        - Complexity (based on task description, dependencies)
        - Reasoning depth (based on task type)
        - Context size (based on project size)
        - Speed priority (based on task urgency)
        - Cost constraint (based on project budget)
        """

        # Heuristic: longer descriptions = more complex
        description_length = len(task.description.split())
        task_complexity = min(description_length / 50.0, 1.0)

        # Heuristic: certain task types require deep reasoning
        reasoning_tasks = ["architecture", "design", "security", "optimization"]
        reasoning_depth = (
            0.9 if any(kw in task.description.lower() for kw in reasoning_tasks) else 0.5
        )

        # Estimate context size from task context
        context_size = task.context.get("estimated_context_tokens", 10_000)

        # Speed priority from task metadata
        speed_priority = task.context.get("speed_priority", 0.5)

        # Cost constraint from task metadata
        cost_constraint = task.context.get("cost_constraint", 0.05)

        # Historical performance (will be learned over time)
        historical_performance = 1.0

        return ModelSelectionCriteria(
            task_complexity=task_complexity,
            reasoning_depth=reasoning_depth,
            context_size=context_size,
            speed_priority=speed_priority,
            cost_constraint=cost_constraint,
            historical_performance=historical_performance,
        )

    def _calculate_model_score(
        self, model: ModelType, capabilities: Dict, criteria: ModelSelectionCriteria
    ) -> float:
        """
        Multi-criteria scoring function.

        Weighted sum of:
        - Reasoning capability match (40%)
        - Context size adequacy (20%)
        - Speed match (20%)
        - Cost efficiency (20%)
        """

        # Reasoning match: how well does model's reasoning strength match requirement?
        reasoning_score = min(
            capabilities["reasoning_strength"] / max(criteria.reasoning_depth, 0.1), 1.0
        )

        # Context adequacy: can model handle required context?
        context_score = 1.0 if capabilities["max_context"] >= criteria.context_size else 0.5

        # Speed match: does speed align with priority?
        speed_score = capabilities["speed_score"] * criteria.speed_priority

        # Cost efficiency: is model within budget?
        cost_score = 1.0 if capabilities["cost_per_1k_tokens"] <= criteria.cost_constraint else 0.3

        # Weighted sum
        total_score = (
            0.4 * reasoning_score + 0.2 * context_score + 0.2 * speed_score + 0.2 * cost_score
        )

        return total_score

    async def update_historical_performance(
        self, agent_type: str, model: ModelType, performance_score: float
    ):
        """
        Update historical performance weights based on task outcomes.

        Uses exponential moving average to track model performance per agent type.
        """

        if agent_type not in self.historical_weights:
            self.historical_weights[agent_type] = {}

        current_weight = self.historical_weights[agent_type].get(model, 1.0)

        # Exponential moving average (alpha = 0.3)
        new_weight = 0.7 * current_weight + 0.3 * performance_score

        self.historical_weights[agent_type][model] = new_weight

        logger.debug(f"Updated {agent_type} performance for {model.value}: {new_weight:.2f}")
