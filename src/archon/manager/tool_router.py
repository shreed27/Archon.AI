"""
Tool Router - Intelligent tool selection logic.
"""

from typing import List, Dict, Optional, Any
from archon.tools.base import BaseTool
from archon.utils.schemas import Task, ToolResult
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class ToolRouter:
    """
    Decides whether to use an AI model or a specialized tool for a task.
    """

    def __init__(self, sandbox=None, learning_engine=None):
        self.sandbox = sandbox
        self.learning_engine = learning_engine
        self.tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        """Register a tool available for use."""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    async def select_best_tool(self, task: Task) -> Optional[str]:
        """
        Determine the best tool for a given task, if any tool is better than AI alone.

        Returns:Tool name or None (use AI)
        """
        candidate_tools = self._find_candidates(task)
        if not candidate_tools:
            return None

        # Score each candidate
        # Compare with AI baseline (0.7 by default)
        ai_baseline_score = 0.7

        best_tool = None
        best_score = 0.0

        for tool_name in candidate_tools:
            tool = self.tools[tool_name]
            score = await self._score_tool(tool, task)

            if score > best_score:
                best_score = score
                best_tool = tool_name

        # Only suggest if strictly better than AI baseline + margin (1.2x ?)
        # Design says: Score > AI * 1.2?
        threshold = ai_baseline_score * 1.2

        if best_score > threshold:
            logger.info(
                f"Tool Router selected '{best_tool}' (score {best_score:.2f} > threshold {threshold:.2f})"
            )
            return best_tool

        return None

    def _find_candidates(self, task: Task) -> List[str]:
        """Identify potential tools based on task description or type."""
        candidates = []
        desc = task.description.lower()

        # Simple keyword matching for now
        # Expand with semantic search later?
        if "diagram" in desc or "visualize" in desc or "architecture" in desc:
            if "eraser_cli" in self.tools:
                candidates.append("eraser_cli")

        if "terraform" in desc or "infrastructure" in desc:
            if "terraform" in self.tools:
                candidates.append("terraform")

        return candidates

    async def _score_tool(self, tool: BaseTool, task: Task) -> float:
        """
        Calculate suitability score for a tool.
        Score = 0.4 * Trust + 0.3 * History + 0.3 * Performance
        """
        # Get history from LearningEngine if available
        history_success = 0.8  # Default baseline
        perf_score = 0.8

        if self.learning_engine:
            # Query learning engine for tool stats
            # Placeholder: implement get_tool_stats
            pass

        # Use tool's trust score
        trust_score = getattr(tool, "trust_score", 0.8)

        final_score = (0.4 * trust_score) + (0.3 * history_success) + (0.3 * perf_score)
        return final_score

    async def execute_tool(self, tool_name: str, input_data: Any) -> ToolResult:
        """Execute selected tool."""
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered")

        tool = self.tools[tool_name]
        return await tool.execute(input_data)
