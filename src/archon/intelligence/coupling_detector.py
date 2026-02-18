"""
Code Coupling Detector - Analyzes module coupling and instability.
"""

from typing import Dict, List
import networkx as nx

from archon.intelligence.dependency_analyzer import DependencyAnalyzer
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class CouplingDetector:
    """
    Analyzes code coupling metrics:
    - Afferent Coupling (Ca): Incoming dependencies
    - Efferent Coupling (Ce): Outgoing dependencies
    - Instability (I): Ce / (Ca + Ce)
    """

    def __init__(self, project_root: str):
        self.analyzer = DependencyAnalyzer(project_root)

    def analyze_coupling(self) -> Dict:
        """
        Calculate coupling metrics for all modules.
        """
        self.analyzer.analyze_project()
        graph = self.analyzer.graph

        metrics = {}

        for node in graph.nodes():
            ca = graph.in_degree(node)  # Afferent coupling (Fan-in)
            ce = graph.out_degree(node)  # Efferent coupling (Fan-out)

            if ca + ce == 0:
                instability = 0.0
            else:
                instability = ce / (ca + ce)

            metrics[node] = {"ca": ca, "ce": ce, "instability": round(instability, 2)}

        # Identify hotspots
        hotspots = self._identify_hotspots(metrics)

        return {
            "metrics": metrics,
            "hotspots": hotspots,
            "average_instability": sum(m["instability"] for m in metrics.values())
            / max(len(metrics), 1),
        }

    def _identify_hotspots(self, metrics: Dict) -> List[Dict]:
        """
        Identify modules that violate stability principles.

        Stable Dependencies Principle (SDP): Depend in direction of stability.
        Modules with high Ca (many dependents) should be stable (low I).
        """
        hotspots = []

        for module, m in metrics.items():
            # Hub-like modules (high fan-in) should not depend on many things (low fan-out)
            # If a module is used by many (high Ca) but depends on many (high Ce), it's a "God Object" or "Hub".
            if m["ca"] > 5 and m["ce"] > 5:
                hotspots.append(
                    {
                        "module": module,
                        "issue": "High Coupling Hub (God Object)",
                        "details": f"Ca={m['ca']}, Ce={m['ce']} - Hard to change without breaking dependents",
                    }
                )

            # Modules with high instability but high fan-in are dangerous
            # (Lots of things depend on it, but it changes often because it depends on many things)
            if m["ca"] > 5 and m["instability"] > 0.7:
                hotspots.append(
                    {
                        "module": module,
                        "issue": "Unstable Core",
                        "details": f"Highly used (Ca={m['ca']}) but unstable (I={m['instability']})",
                    }
                )

        return hotspots
