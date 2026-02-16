"""
Arbitrator - Multi-agent conflict resolution and deliberation.
"""

from typing import Dict, List, Optional
import uuid
from datetime import datetime

from archon.utils.schemas import (
    Task,
    TaskResult,
    Conflict,
    AgentProposal,
    Decision,
)


class Arbitrator:
    """
    Handles multi-agent deliberation and conflict resolution.
    Manager uses this when multiple agents propose different solutions.
    """

    def __init__(self):
        self.conflicts: Dict[str, Conflict] = {}
        self.decisions: List[Decision] = []

    async def resolve_conflict(self, task: Task, proposals: List[AgentProposal]) -> Decision:
        """
        Resolve conflict between multiple agent proposals.

        Args:
            task: The task being deliberated
            proposals: List of agent proposals

        Returns:
            Manager's decision on which proposal to accept
        """
        conflict_id = f"conflict_{uuid.uuid4().hex[:8]}"

        conflict = Conflict(
            conflict_id=conflict_id,
            conflict_type="multi_agent_proposal",
            agents_involved=[p.agent for p in proposals],
            proposals=proposals,
            task_id=task.task_id,
        )

        self.conflicts[conflict_id] = conflict

        # Score each proposal
        scored_proposals = []
        for proposal in proposals:
            score = self._score_proposal(proposal, task)
            scored_proposals.append((score, proposal))

        # Sort by score (highest first)
        scored_proposals.sort(key=lambda x: x[0], reverse=True)
        best_score, best_proposal = scored_proposals[0]

        # Create decision
        decision = Decision(
            conflict_id=conflict_id,
            chosen_agent=best_proposal.agent,
            chosen_proposal=best_proposal.proposal,
            reasoning=self._generate_reasoning(scored_proposals, task),
            timestamp=datetime.now(),
        )

        self.decisions.append(decision)
        return decision

    def _score_proposal(self, proposal: AgentProposal, task: Task) -> float:
        """
        Score a proposal based on multiple criteria.

        Scoring factors:
        - Lower risk is better
        - Lower complexity is better (for MVP)
        - Faster estimated time is better
        - Agent expertise match
        """
        # Base score
        score = 100.0

        # Risk penalty (0.0 to 1.0, lower is better)
        score -= proposal.risk_score * 30

        # Complexity penalty (0.0 to 1.0, lower is better for MVP)
        score -= proposal.complexity_score * 20

        # Time penalty (prefer faster solutions)
        time_penalty = min(proposal.estimated_time_hours / 10.0, 1.0) * 15
        score -= time_penalty

        # Reasoning quality bonus (longer, more detailed reasoning)
        reasoning_bonus = min(len(proposal.reasoning) / 500.0, 1.0) * 10
        score += reasoning_bonus

        return max(score, 0.0)

    def _generate_reasoning(self, scored_proposals: List[tuple], task: Task) -> str:
        """Generate human-readable reasoning for the decision."""
        best_score, best_proposal = scored_proposals[0]

        reasoning = f"Selected {best_proposal.agent}'s proposal (score: {best_score:.1f}).\n\n"
        reasoning += f"Rationale:\n{best_proposal.reasoning}\n\n"
        reasoning += f"Risk: {best_proposal.risk_score:.2f}, "
        reasoning += f"Complexity: {best_proposal.complexity_score:.2f}, "
        reasoning += f"Est. Time: {best_proposal.estimated_time_hours:.1f}h\n\n"

        if len(scored_proposals) > 1:
            reasoning += "Alternative proposals considered:\n"
            for score, proposal in scored_proposals[1:]:
                reasoning += f"- {proposal.agent} (score: {score:.1f}): "
                reasoning += f"{proposal.proposal[:100]}...\n"

        return reasoning

    async def check_needs_deliberation(self, result: TaskResult) -> bool:
        """
        Check if a task result needs multi-agent deliberation.

        Triggers deliberation if:
        - Quality score is borderline (0.7-0.8)
        - Security-critical task
        - Architecture changes proposed
        """
        if result.needs_deliberation:
            return True

        # Borderline quality
        if 0.7 <= result.quality_score <= 0.8:
            return True

        # Architecture changes need review
        if result.architecture_changes:
            return True

        return False

    async def request_alternative_proposals(
        self, task: Task, initial_result: TaskResult
    ) -> List[AgentProposal]:
        """
        Request alternative proposals from other agents.

        In production, this would:
        1. Identify relevant agents for the task
        2. Send task context to each agent
        3. Collect their proposals
        4. Return for arbitration

        For now, returns placeholder structure.
        """
        # This would be implemented to actually query other agents
        # For now, return empty list (single agent decision)
        return []

    def get_conflict_history(self, task_id: Optional[str] = None) -> List[Conflict]:
        """Get conflict history, optionally filtered by task."""
        if task_id:
            return [c for c in self.conflicts.values() if c.task_id == task_id]
        return list(self.conflicts.values())

    def get_decision_history(self) -> List[Decision]:
        """Get all arbitration decisions."""
        return self.decisions
