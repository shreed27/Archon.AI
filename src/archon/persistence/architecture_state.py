"""
Architecture State - Track and detect architecture drift.
"""

import json
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ArchitectureChange:
    """Record of an architecture change."""

    timestamp: str
    change_type: str  # "component_added", "pattern_changed", "dependency_added", etc.
    description: str
    rationale: str
    impact: str
    agent: str


class ArchitectureState:
    """
    Tracks current architecture state and detects drift.
    Maintains history of architecture decisions.
    """

    def __init__(self, path: str):
        self.path = path
        self.current_state: Dict = {}
        self.change_history: List[ArchitectureChange] = []

    async def initialize(self):
        """Initialize architecture state, load if exists."""
        state_path = Path(self.path)
        if state_path.exists():
            await self._load_state()
        else:
            state_path.parent.mkdir(parents=True, exist_ok=True)
            self.current_state = self._get_default_state()
            await self._save_state()

    async def apply_changes(self, changes: Dict):
        """
        Apply architecture changes and record them.

        Args:
            changes: Dictionary containing architecture changes
        """
        change_record = ArchitectureChange(
            timestamp=datetime.now().isoformat(),
            change_type=changes.get("type", "unknown"),
            description=changes.get("description", ""),
            rationale=changes.get("rationale", ""),
            impact=changes.get("impact", ""),
            agent=changes.get("agent", "unknown"),
        )

        self.change_history.append(change_record)

        # Update current state
        if "components" in changes:
            self.current_state.setdefault("components", []).extend(changes["components"])

        if "patterns" in changes:
            self.current_state.setdefault("patterns", {}).update(changes["patterns"])

        if "dependencies" in changes:
            self.current_state.setdefault("dependencies", []).extend(changes["dependencies"])

        if "tech_stack" in changes:
            self.current_state.setdefault("tech_stack", {}).update(changes["tech_stack"])

        await self._save_state()

    async def get_current_state(self) -> Dict:
        """Get current architecture state."""
        return self.current_state.copy()

    async def detect_drift(self, proposed_changes: Dict) -> Dict:
        """
        Detect if proposed changes would cause architecture drift.

        Args:
            proposed_changes: Proposed architecture changes

        Returns:
            Dictionary with drift analysis
        """
        drift_analysis = {
            "has_drift": False,
            "drift_type": [],
            "severity": "none",  # none, low, medium, high
            "recommendations": [],
        }

        # Check for pattern violations
        if "patterns" in proposed_changes:
            current_patterns = self.current_state.get("patterns", {})
            for pattern_name, pattern_value in proposed_changes["patterns"].items():
                if pattern_name in current_patterns:
                    if current_patterns[pattern_name] != pattern_value:
                        drift_analysis["has_drift"] = True
                        drift_analysis["drift_type"].append("pattern_change")
                        drift_analysis["recommendations"].append(
                            f"Pattern '{pattern_name}' is changing from "
                            f"'{current_patterns[pattern_name]}' to '{pattern_value}'"
                        )

        # Check for tech stack changes
        if "tech_stack" in proposed_changes:
            current_stack = self.current_state.get("tech_stack", {})
            for tech, version in proposed_changes["tech_stack"].items():
                if tech in current_stack and current_stack[tech] != version:
                    drift_analysis["has_drift"] = True
                    drift_analysis["drift_type"].append("tech_stack_change")
                    drift_analysis["severity"] = "medium"

        # Check for new major components
        if "components" in proposed_changes:
            new_components = [
                c
                for c in proposed_changes["components"]
                if c not in self.current_state.get("components", [])
            ]
            if new_components:
                drift_analysis["drift_type"].append("new_components")
                drift_analysis["recommendations"].append(
                    f"Adding new components: {', '.join(new_components)}"
                )

        # Determine severity
        if drift_analysis["has_drift"]:
            if "pattern_change" in drift_analysis["drift_type"]:
                drift_analysis["severity"] = "high"
            elif "tech_stack_change" in drift_analysis["drift_type"]:
                drift_analysis["severity"] = "medium"
            else:
                drift_analysis["severity"] = "low"

        return drift_analysis

    async def get_change_history(self, limit: Optional[int] = None) -> List[ArchitectureChange]:
        """Get architecture change history."""
        if limit:
            return self.change_history[-limit:]
        return self.change_history.copy()

    async def get_components(self) -> List[str]:
        """Get list of current architecture components."""
        return self.current_state.get("components", [])

    async def get_patterns(self) -> Dict:
        """Get current architecture patterns."""
        return self.current_state.get("patterns", {})

    async def export_architecture_doc(self) -> str:
        """Export current architecture as markdown documentation."""
        doc = "# Current Architecture\n\n"
        doc += f"Last updated: {datetime.now().isoformat()}\n\n"

        doc += "## Components\n\n"
        for component in self.current_state.get("components", []):
            doc += f"- {component}\n"

        doc += "\n## Patterns\n\n"
        for pattern, value in self.current_state.get("patterns", {}).items():
            doc += f"- **{pattern}**: {value}\n"

        doc += "\n## Tech Stack\n\n"
        for tech, version in self.current_state.get("tech_stack", {}).items():
            doc += f"- {tech}: {version}\n"

        doc += "\n## Recent Changes\n\n"
        recent_changes = self.change_history[-5:]
        for change in recent_changes:
            doc += f"### {change.timestamp}\n"
            doc += f"**Type**: {change.change_type}\n\n"
            doc += f"{change.description}\n\n"

        return doc

    def _get_default_state(self) -> Dict:
        """Get default architecture state."""
        return {
            "components": [],
            "patterns": {},
            "dependencies": [],
            "tech_stack": {},
            "created_at": datetime.now().isoformat(),
        }

    async def _save_state(self):
        """Save architecture state to disk."""
        data = {
            "current_state": self.current_state,
            "change_history": [asdict(change) for change in self.change_history],
        }
        Path(self.path).write_text(json.dumps(data, indent=2))

    async def _load_state(self):
        """Load architecture state from disk."""
        try:
            data = json.loads(Path(self.path).read_text())
            self.current_state = data.get("current_state", self._get_default_state())
            self.change_history = [
                ArchitectureChange(**change) for change in data.get("change_history", [])
            ]
        except Exception:
            self.current_state = self._get_default_state()
            self.change_history = []
