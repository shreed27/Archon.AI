"""
Drift Detector - Compares implementation against architecture specifications.
"""

from typing import Dict, List, Set, Tuple
import networkx as nx

from archon.persistence.architecture_state import ArchitectureState
from archon.intelligence.dependency_analyzer import DependencyAnalyzer
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class DriftDetector:
    """
    Identifies architectural drift:
    - New modules not in spec
    - Dependencies violating layer boundaries
    - Unexpected complexity growth
    """

    def __init__(self, project_root: str, expected_architecture: ArchitectureState):
        self.analyzer = DependencyAnalyzer(project_root)
        self.expected_arch = expected_architecture

    def detect_drift(self) -> Dict:
        """
        Compare current codebase state vs expected architecture state.
        """
        # Populate dependency graph
        self.analyzer.analyze_project()
        graph = self.analyzer.graph

        # 1. Component Drift
        implemented_modules = set(graph.nodes())
        expected_modules = set(self.expected_arch.get_component_names())

        unexpected_modules = implemented_modules - expected_modules
        missing_modules = expected_modules - implemented_modules

        # 2. Dependency Rule Violations (e.g. Domain layer depends on Infrastructure)
        violations = self._check_layer_violations(graph)

        drift_report = {
            "unexpected_modules": list(unexpected_modules),
            "missing_modules": list(missing_modules),
            "layer_violations": violations,
            "drift_score": self._calculate_drift_score(len(unexpected_modules), len(violations)),
        }

        if drift_report["drift_score"] > 0.3:
            logger.warning(f"High architectural drift detected: {drift_report['drift_score']}")

        return drift_report

    def _check_layer_violations(self, graph: nx.DiGraph) -> List[Dict]:
        """Check for forbidden dependencies between layers."""
        violations = []
        for u, v in graph.edges():
            u_layer = self._get_layer(u)
            v_layer = self._get_layer(v)

            if self._is_forbidden(u_layer, v_layer):
                violations.append(
                    {
                        "source": u,
                        "target": v,
                        "violation": f"Layer violation: {u_layer} cannot depend on {v_layer}",
                    }
                )
        return violations

    def _get_layer(self, module_name: str) -> str:
        # Simple heuristic mapping - in production this would use ArchitectureState
        if "domain" in module_name:
            return "domain"
        if "application" in module_name or "use_cases" in module_name:
            return "application"
        if "infrastructure" in module_name:
            return "infrastructure"
        if "presentation" in module_name or "api" in module_name:
            return "presentation"
        return "unknown"

    def _is_forbidden(self, source_layer: str, target_layer: str) -> bool:
        # Strict Clean Architecture / Onion Architecture rules
        # Inner layers cannot depend on outer layers

        # Define layer ordering (inner to outer)
        layers = ["domain", "application", "infrastructure", "presentation"]

        try:
            src_idx = layers.index(source_layer)
            tgt_idx = layers.index(target_layer)

            # Violation if source (inner) depends on target (outer)
            # Actually, typically Infra depends on App/Domain. Presentation depends on App.
            # Domain depends on nothing.

            # Correct Clean Architecture dependency rule: dependencies point INWARDS.
            # So generic `source -> target` means source depends on target.
            # If `source` is inner (lower index) and `target` is outer (higher index), that's a VIOLATION.

            # Wait, order:
            # 0: Domain (Core)
            # 1: Application (Use Cases) - Depends on Domain
            # 2: Infrastructure / Presentation - Depends on Application

            if src_idx < tgt_idx:
                return True

        except ValueError:
            pass  # Layer unknown

        return False

    def _calculate_drift_score(self, unexpected_count: int, violation_count: int) -> float:
        return min((unexpected_count * 0.1) + (violation_count * 0.2), 1.0)
