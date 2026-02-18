"""
Dependency Analyzer - Maps internal and external dependencies.
"""

from typing import Dict, List, Set
from pathlib import Path
import networkx as nx

from archon.intelligence.ast_parser import ASTParser
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class DependencyAnalyzer:
    """
    Analyzes project dependencies to detect:
    - Circular dependencies
    - External library usage
    - Tight coupling between modules
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.parser = ASTParser()
        self.graph = nx.DiGraph()
        self.external_deps: Set[str] = set()

    def analyze_project(self) -> Dict:
        """
        Scan the entire project and build a dependency graph.
        """
        logger.info(f"Analyzing dependencies for {self.project_root}")

        python_files = list(self.project_root.glob("**/*.py"))

        for file_path in python_files:
            relative_path = file_path.relative_to(self.project_root)
            module_name = str(relative_path).replace("/", ".").replace(".py", "")

            self.graph.add_node(module_name, file=str(file_path))

            analysis = self.parser.parse_file(file_path)
            if not analysis:
                continue

            for imprt in analysis.get("imports", []):
                target_module = imprt["module"]

                if self._is_internal_module(target_module):
                    self.graph.add_edge(module_name, target_module)
                else:
                    self.external_deps.add(target_module.split(".")[0])

        return {
            "graph_size": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "detected_cycles": list(nx.simple_cycles(self.graph)),
            "external_dependencies": list(self.external_deps),
            "high_fan_in_modules": self._get_high_fan_in(),
            "high_fan_out_modules": self._get_high_fan_out(),
        }

    def _is_internal_module(self, module_name: str) -> bool:
        """Check if a module is part of the project."""
        # Simplified check: assume internal if it starts with 'archon' or project name
        # A more robust check would verify file existence.
        # For now, let's check if the module path exists relative to src
        potential_path = self.project_root / "src" / module_name.replace(".", "/")
        return (
            potential_path.exists()
            or (potential_path.parent / (potential_path.name + ".py")).exists()
        )

    def _get_high_fan_in(self, threshold=5) -> List[str]:
        """Modules that many other modules depend on (utilities, core)."""
        return [n for n, d in self.graph.in_degree() if d >= threshold]

    def _get_high_fan_out(self, threshold=5) -> List[str]:
        """Modules that depend on many other modules (potential god objects)."""
        return [n for n, d in self.graph.out_degree() if d >= threshold]
