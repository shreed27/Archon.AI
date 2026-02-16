"""
Task Graph - DAG persistence and visualization.
"""

import json
import networkx as nx
from typing import List, Dict, Optional
from pathlib import Path

from archon.utils.schemas import Task, TaskStatus


class TaskGraph:
    """
    Manages task dependency graph (DAG).
    Uses NetworkX for graph operations and analysis.
    """

    def __init__(self, path: str):
        self.path = path
        self.graph: nx.DiGraph = nx.DiGraph()

    async def initialize(self):
        """Initialize task graph, load if exists."""
        graph_path = Path(self.path)
        if graph_path.exists():
            await self._load_graph()
        else:
            graph_path.parent.mkdir(parents=True, exist_ok=True)

    async def store_tasks(self, tasks: List[Task]):
        """
        Store tasks as DAG.

        Args:
            tasks: List of tasks with dependencies
        """
        self.graph.clear()

        # Add nodes
        for task in tasks:
            self.graph.add_node(
                task.task_id,
                description=task.description,
                agent_type=task.agent_type.value,
                status=task.status.value,
                quality_threshold=task.quality_threshold,
                created_at=task.created_at.isoformat(),
            )

        # Add edges (dependencies)
        for task in tasks:
            for dep_id in task.dependencies:
                # Edge from dependency to task (dep must complete before task)
                self.graph.add_edge(dep_id, task.task_id)

        await self._save_graph()

    async def update_task_status(self, task_id: str, status: TaskStatus):
        """Update task status in graph."""
        if task_id in self.graph.nodes:
            self.graph.nodes[task_id]["status"] = status.value
            await self._save_graph()

    async def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get all dependencies for a task."""
        if task_id not in self.graph.nodes:
            return []
        return list(self.graph.predecessors(task_id))

    async def get_dependent_tasks(self, task_id: str) -> List[str]:
        """Get all tasks that depend on this task."""
        if task_id not in self.graph.nodes:
            return []
        return list(self.graph.successors(task_id))

    async def get_execution_levels(self) -> List[List[str]]:
        """
        Get task execution levels (topological generations).
        Tasks in the same level can execute in parallel.
        """
        try:
            # Get topological generations
            levels = list(nx.topological_generations(self.graph))
            return levels
        except nx.NetworkXError:
            # Graph has cycles or is empty
            return []

    async def get_critical_path(self) -> List[str]:
        """
        Get critical path (longest path through DAG).
        This represents the minimum time to complete all tasks.
        """
        if not self.graph.nodes:
            return []

        try:
            # Find longest path
            path_lengths = nx.dag_longest_path_length(self.graph)
            longest_path = nx.dag_longest_path(self.graph)
            return longest_path
        except nx.NetworkXError:
            return []

    async def is_valid_dag(self) -> bool:
        """Check if graph is a valid DAG (no cycles)."""
        return nx.is_directed_acyclic_graph(self.graph)

    async def get_graph_stats(self) -> Dict:
        """Get graph statistics."""
        return {
            "total_tasks": self.graph.number_of_nodes(),
            "total_dependencies": self.graph.number_of_edges(),
            "is_valid_dag": await self.is_valid_dag(),
            "max_depth": (
                nx.dag_longest_path_length(self.graph) if await self.is_valid_dag() else 0
            ),
        }

    async def export_dot(self) -> str:
        """Export graph as DOT format for visualization."""
        try:
            from networkx.drawing.nx_pydot import to_pydot

            pydot_graph = to_pydot(self.graph)
            return pydot_graph.to_string()
        except ImportError:
            # Fallback to simple text representation
            return str(self.graph.edges())

    async def _save_graph(self):
        """Save graph to JSON file."""
        data = {
            "nodes": [{"id": node, **self.graph.nodes[node]} for node in self.graph.nodes],
            "edges": [{"source": u, "target": v} for u, v in self.graph.edges],
        }

        Path(self.path).write_text(json.dumps(data, indent=2))

    async def _load_graph(self):
        """Load graph from JSON file."""
        try:
            data = json.loads(Path(self.path).read_text())

            self.graph.clear()

            # Add nodes
            for node_data in data.get("nodes", []):
                node_id = node_data.pop("id")
                self.graph.add_node(node_id, **node_data)

            # Add edges
            for edge_data in data.get("edges", []):
                self.graph.add_edge(edge_data["source"], edge_data["target"])

        except Exception:
            # If loading fails, start with empty graph
            self.graph = nx.DiGraph()
