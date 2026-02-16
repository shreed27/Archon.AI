"""
Tool Registry - Catalog of available external tools.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories."""

    DIAGRAM = "diagram"
    INFRASTRUCTURE = "infrastructure"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ANALYSIS = "analysis"
    DOCUMENTATION = "documentation"


@dataclass
class ToolSpec:
    """Specification for an external tool."""

    name: str
    category: ToolCategory
    command: str
    description: str
    install_command: Optional[str] = None
    required_args: List[str] = None
    optional_args: List[str] = None
    output_format: str = "text"  # text, json, svg, etc.
    quality_score: float = 0.8  # Historical quality score

    def __post_init__(self):
        if self.required_args is None:
            self.required_args = []
        if self.optional_args is None:
            self.optional_args = []


class ToolRegistry:
    """
    Registry of available external tools.
    Maintains catalog of tools and their specifications.
    """

    def __init__(self):
        self.tools: Dict[str, ToolSpec] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register default set of tools."""

        # Diagram generation
        self.register(
            ToolSpec(
                name="eraser-cli",
                category=ToolCategory.DIAGRAM,
                command="eraser-cli",
                description="Generate system architecture diagrams from text descriptions",
                install_command="npm install -g eraser-cli",
                required_args=["description"],
                optional_args=["output", "format"],
                output_format="svg",
                quality_score=0.95,
            )
        )

        # Infrastructure as Code
        self.register(
            ToolSpec(
                name="terraform",
                category=ToolCategory.INFRASTRUCTURE,
                command="terraform",
                description="Infrastructure as Code tool for cloud resources",
                required_args=["action"],
                optional_args=["var-file", "auto-approve"],
                output_format="text",
                quality_score=0.92,
            )
        )

        # Testing
        self.register(
            ToolSpec(
                name="playwright",
                category=ToolCategory.TESTING,
                command="playwright",
                description="End-to-end testing for web applications",
                install_command="npm install -g playwright",
                required_args=["test"],
                optional_args=["browser", "headed"],
                output_format="json",
                quality_score=0.88,
            )
        )

        # Code analysis
        self.register(
            ToolSpec(
                name="ruff",
                category=ToolCategory.ANALYSIS,
                command="ruff",
                description="Fast Python linter",
                install_command="pip install ruff",
                required_args=["path"],
                optional_args=["fix", "format"],
                output_format="json",
                quality_score=0.90,
            )
        )

        # Documentation
        self.register(
            ToolSpec(
                name="sphinx",
                category=ToolCategory.DOCUMENTATION,
                command="sphinx-build",
                description="Python documentation generator",
                install_command="pip install sphinx",
                required_args=["source", "output"],
                optional_args=["builder"],
                output_format="html",
                quality_score=0.85,
            )
        )

    def register(self, tool: ToolSpec):
        """Register a new tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        """Get tool specification by name."""
        return self.tools.get(name)

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolSpec]:
        """Get all tools in a category."""
        return [tool for tool in self.tools.values() if tool.category == category]

    def search_tools(self, query: str) -> List[ToolSpec]:
        """Search tools by name or description."""
        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)

        return results

    def get_best_tool_for_task(self, task_description: str) -> Optional[ToolSpec]:
        """
        Find best tool for a task based on description.

        Args:
            task_description: Description of the task

        Returns:
            Best matching tool or None
        """
        task_lower = task_description.lower()

        # Simple keyword matching
        keywords_to_category = {
            "diagram": ToolCategory.DIAGRAM,
            "architecture": ToolCategory.DIAGRAM,
            "infrastructure": ToolCategory.INFRASTRUCTURE,
            "terraform": ToolCategory.INFRASTRUCTURE,
            "test": ToolCategory.TESTING,
            "testing": ToolCategory.TESTING,
            "lint": ToolCategory.ANALYSIS,
            "analyze": ToolCategory.ANALYSIS,
            "document": ToolCategory.DOCUMENTATION,
            "docs": ToolCategory.DOCUMENTATION,
        }

        # Find matching category
        for keyword, category in keywords_to_category.items():
            if keyword in task_lower:
                tools = self.get_tools_by_category(category)
                if tools:
                    # Return tool with highest quality score
                    return max(tools, key=lambda t: t.quality_score)

        return None

    def list_all_tools(self) -> List[ToolSpec]:
        """Get list of all registered tools."""
        return list(self.tools.values())

    def get_tool_count(self) -> int:
        """Get total number of registered tools."""
        return len(self.tools)

    def update_quality_score(self, tool_name: str, new_score: float):
        """Update quality score for a tool based on performance."""
        if tool_name in self.tools:
            self.tools[tool_name].quality_score = new_score

    def export_catalog(self) -> Dict:
        """Export tool catalog as dictionary."""
        return {
            name: {
                "category": tool.category.value,
                "command": tool.command,
                "description": tool.description,
                "install_command": tool.install_command,
                "quality_score": tool.quality_score,
            }
            for name, tool in self.tools.items()
        }
