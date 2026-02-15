"""
Tool Router - Decides when to use external CLI tools instead of AI models.

Critical innovation: Manager can choose external tools when superior to AI.
"""

from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path
import json

from archon.utils.schemas import Task
from archon.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExternalTool:
    """External CLI tool definition."""

    name: str
    description: str
    task_types_supported: List[str]
    installation_method: str
    sandbox_required: bool
    trust_score: float
    performance_score: float
    avg_execution_time_ms: int
    success_rate: float
    output_format: str
    validation_schema: dict
    requires_credentials: bool = False


@dataclass
class ToolDecision:
    """Decision on whether to use external tool."""

    use_tool: bool
    tool: Optional[ExternalTool]
    reasoning: str
    confidence: float


class ToolRouter:
    """
    Decides when to use external CLI tools instead of AI models.

    Decision criteria:
    - Capability match: Does tool support this task type?
    - Accuracy advantage: Is tool more accurate than AI?
    - Performance history: Has tool performed well historically?
    - Trust score: Is tool from trusted source?

    Examples of when to use tools:
    - System design diagrams → Eraser CLI (specialized, deterministic)
    - Infrastructure provisioning → Terraform (industry standard)
    - E2E testing → Playwright (purpose-built)
    - Static analysis → Semgrep (specialized)
    """

    # AI baseline performance by task type (learned over time)
    AI_BASELINE_SCORES = {
        "system_design_diagram": 0.70,
        "architecture_diagram": 0.68,
        "infrastructure_provisioning": 0.60,
        "e2e_testing": 0.75,
        "static_analysis": 0.80,
        "default": 0.70,
    }

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path
        self.tools: List[ExternalTool] = []
        self.tool_history: dict = {}

    async def initialize(self, archon_dir: Path):
        """Initialize tool registry."""

        registry_file = archon_dir / "tool_registry.json"

        if registry_file.exists():
            await self._load_registry(registry_file)
        else:
            await self._create_default_registry(registry_file)

    async def _load_registry(self, registry_file: Path):
        """Load tool registry from file."""

        with open(registry_file) as f:
            data = json.load(f)

        self.tools = [ExternalTool(**tool) for tool in data.get("tools", [])]
        logger.info(f"Loaded {len(self.tools)} tools from registry")

    async def _create_default_registry(self, registry_file: Path):
        """Create default tool registry with common tools."""

        default_tools = [
            {
                "name": "eraser-cli",
                "description": "Generate system design diagrams",
                "task_types_supported": [
                    "system_design_diagram",
                    "architecture_diagram",
                    "sequence_diagram",
                ],
                "installation_method": "npm install -g eraser-cli",
                "sandbox_required": True,
                "trust_score": 0.95,
                "performance_score": 0.92,
                "avg_execution_time_ms": 1500,
                "success_rate": 0.98,
                "output_format": "svg",
                "validation_schema": {"type": "file", "extension": ".svg", "min_size_bytes": 1000},
            },
            {
                "name": "terraform",
                "description": "Infrastructure as code",
                "task_types_supported": ["infrastructure_provisioning", "cloud_deployment"],
                "installation_method": "brew install terraform",
                "sandbox_required": True,
                "trust_score": 0.98,
                "performance_score": 0.95,
                "avg_execution_time_ms": 5000,
                "success_rate": 0.96,
                "output_format": "terraform_state",
                "validation_schema": {"type": "terraform_state"},
                "requires_credentials": True,
            },
            {
                "name": "playwright",
                "description": "E2E testing framework",
                "task_types_supported": ["e2e_testing", "browser_automation"],
                "installation_method": "npm install -g playwright",
                "sandbox_required": True,
                "trust_score": 0.97,
                "performance_score": 0.94,
                "avg_execution_time_ms": 10000,
                "success_rate": 0.93,
                "output_format": "test_results",
                "validation_schema": {"type": "test_results"},
            },
        ]

        registry_data = {"tools": default_tools}

        with open(registry_file, "w") as f:
            json.dump(registry_data, f, indent=2)

        self.tools = [ExternalTool(**tool) for tool in default_tools]
        logger.info(f"Created default registry with {len(self.tools)} tools")

    async def should_use_tool(self, task: Task) -> ToolDecision:
        """
        Determine if external tool is better than AI model.

        Algorithm:
        1. Find candidate tools that support this task type
        2. Score each tool based on performance metrics
        3. Compare best tool score with AI baseline
        4. Return decision with reasoning

        Threshold: Tool must be 20% better than AI to be selected
        """

        # Extract task type from description
        task_type = self._infer_task_type(task.description)

        # Find candidate tools
        candidates = [tool for tool in self.tools if task_type in tool.task_types_supported]

        if not candidates:
            return ToolDecision(
                use_tool=False,
                tool=None,
                reasoning=f"No tools found for task type: {task_type}",
                confidence=1.0,
            )

        # Score each tool
        best_tool = None
        best_score = 0.0

        for tool in candidates:
            score = self._score_tool(tool, task)
            if score > best_score:
                best_score = score
                best_tool = tool

        # Get AI baseline for this task type
        ai_baseline = self.AI_BASELINE_SCORES.get(task_type, self.AI_BASELINE_SCORES["default"])

        # Decision threshold: tool must be 20% better
        threshold_multiplier = 1.2

        if best_score > ai_baseline * threshold_multiplier:
            improvement_pct = (best_score / ai_baseline - 1) * 100
            return ToolDecision(
                use_tool=True,
                tool=best_tool,
                reasoning=(
                    f"{best_tool.name} outperforms AI by {improvement_pct:.1f}% "
                    f"(tool: {best_score:.2f}, AI baseline: {ai_baseline:.2f})"
                ),
                confidence=best_score,
            )
        else:
            return ToolDecision(
                use_tool=False,
                tool=None,
                reasoning=(
                    f"AI model performance ({ai_baseline:.2f}) is competitive with "
                    f"best tool ({best_score:.2f})"
                ),
                confidence=ai_baseline,
            )

    def _infer_task_type(self, description: str) -> str:
        """
        Infer task type from description using keyword matching.

        In production, this would use NLP/embeddings for better classification.
        """

        description_lower = description.lower()

        if any(kw in description_lower for kw in ["diagram", "architecture", "design"]):
            if "system" in description_lower:
                return "system_design_diagram"
            return "architecture_diagram"

        if any(kw in description_lower for kw in ["infrastructure", "deploy", "provision"]):
            return "infrastructure_provisioning"

        if any(kw in description_lower for kw in ["e2e", "end-to-end", "browser test"]):
            return "e2e_testing"

        if any(kw in description_lower for kw in ["static analysis", "lint", "security scan"]):
            return "static_analysis"

        return "general"

    def _score_tool(self, tool: ExternalTool, task: Task) -> float:
        """
        Score tool suitability for task.

        Factors:
        - Trust score (40%): Is tool from trusted source?
        - Success rate (30%): Historical success rate
        - Performance score (30%): Quality of outputs
        """

        score = 0.4 * tool.trust_score + 0.3 * tool.success_rate + 0.3 * tool.performance_score

        return score

    async def record_tool_usage(
        self, tool_name: str, task_type: str, success: bool, execution_time_ms: int
    ):
        """Record tool usage for learning."""

        if tool_name not in self.tool_history:
            self.tool_history[tool_name] = {"executions": 0, "successes": 0, "total_time_ms": 0}

        history = self.tool_history[tool_name]
        history["executions"] += 1
        if success:
            history["successes"] += 1
        history["total_time_ms"] += execution_time_ms

        # Update tool metrics
        for tool in self.tools:
            if tool.name == tool_name:
                tool.success_rate = history["successes"] / history["executions"]
                tool.avg_execution_time_ms = history["total_time_ms"] // history["executions"]
                break
