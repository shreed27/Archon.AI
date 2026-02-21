"""Data factories for test fixtures.

These factory functions create sample instances of schema objects
for use in tests. All functions provide sensible defaults that can
be overridden as needed.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from archon.utils.schemas import (
    Task,
    TaskResult,
    TaskStatus,
    AgentType,
    FileChange,
    Decision,
    Conflict,
    AgentProposal,
    QualityCheck,
    AgentMetrics,
    ToolResult,
    ProjectSpec,
)


def create_sample_task(
    task_id: Optional[str] = None,
    description: str = "Test task description",
    agent_type: AgentType = AgentType.BACKEND,
    model_assigned: Optional[str] = None,
    tool_assigned: Optional[str] = None,
    status: TaskStatus = TaskStatus.PENDING,
    dependencies: Optional[List[str]] = None,
    quality_threshold: float = 0.8,
    context: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
) -> Task:
    """Create a sample Task for testing.

    Args:
        task_id: Unique task identifier (auto-generated if not provided)
        description: Task description text
        agent_type: Type of agent to handle the task
        model_assigned: Assigned AI model (optional)
        tool_assigned: Assigned external tool (optional)
        status: Current task status
        dependencies: List of dependent task IDs
        quality_threshold: Minimum quality score required
        context: Additional context dictionary
        created_at: Creation timestamp
        completed_at: Completion timestamp (if completed)

    Returns:
        A Task instance with the specified or default values
    """
    return Task(
        task_id=task_id or f"task_{uuid.uuid4().hex[:8]}",
        description=description,
        agent_type=agent_type,
        model_assigned=model_assigned,
        tool_assigned=tool_assigned,
        status=status,
        dependencies=dependencies or [],
        quality_threshold=quality_threshold,
        context=context or {},
        created_at=created_at or datetime.now(),
        completed_at=completed_at,
    )


def create_sample_task_result(
    task_id: Optional[str] = None,
    success: bool = True,
    output: Optional[Any] = None,
    files_modified: Optional[List[FileChange]] = None,
    quality_score: float = 0.9,
    execution_time_ms: int = 1500,
    model_used: Optional[str] = "gpt-4-turbo",
    tool_used: Optional[str] = None,
    needs_deliberation: bool = False,
    architecture_changes: Optional[Dict] = None,
    error: Optional[str] = None,
) -> TaskResult:
    """Create a sample TaskResult for testing.

    Args:
        task_id: ID of the associated task
        success: Whether task execution succeeded
        output: Task output (dict or string)
        files_modified: List of file changes made
        quality_score: Quality score (0.0-1.0)
        execution_time_ms: Execution time in milliseconds
        model_used: AI model used for execution
        tool_used: External tool used (if any)
        needs_deliberation: Whether multi-agent review is needed
        architecture_changes: Any architecture modifications
        error: Error message if failed

    Returns:
        A TaskResult instance with the specified or default values
    """
    return TaskResult(
        task_id=task_id or f"task_{uuid.uuid4().hex[:8]}",
        success=success,
        output=output or {"result": "Test output", "details": {}},
        files_modified=files_modified or [],
        quality_score=quality_score,
        execution_time_ms=execution_time_ms,
        model_used=model_used,
        tool_used=tool_used,
        needs_deliberation=needs_deliberation,
        architecture_changes=architecture_changes,
        error=error,
    )


def create_sample_file_change(
    path: str = "src/test_file.py",
    change_type: str = "modify",
    lines_added: int = 10,
    lines_removed: int = 5,
    agent: str = "backend",
) -> FileChange:
    """Create a sample FileChange for testing.

    Args:
        path: File path that was changed
        change_type: Type of change ("create", "modify", "delete")
        lines_added: Number of lines added
        lines_removed: Number of lines removed
        agent: Agent that made the change

    Returns:
        A FileChange instance with the specified or default values
    """
    return FileChange(
        path=path,
        change_type=change_type,
        lines_added=lines_added,
        lines_removed=lines_removed,
        agent=agent,
    )


def create_sample_agent_proposal(
    agent: str = "backend",
    proposal: str = "Implement feature using factory pattern",
    reasoning: str = "Factory pattern provides better extensibility",
    risk_score: float = 0.3,
    complexity_score: float = 0.5,
    estimated_time_hours: float = 4.0,
) -> AgentProposal:
    """Create a sample AgentProposal for testing.

    Args:
        agent: Agent identifier
        proposal: Proposed solution description
        reasoning: Justification for the proposal
        risk_score: Estimated risk (0.0-1.0)
        complexity_score: Estimated complexity (0.0-1.0)
        estimated_time_hours: Estimated hours to complete

    Returns:
        An AgentProposal instance with the specified or default values
    """
    return AgentProposal(
        agent=agent,
        proposal=proposal,
        reasoning=reasoning,
        risk_score=risk_score,
        complexity_score=complexity_score,
        estimated_time_hours=estimated_time_hours,
    )


def create_sample_conflict(
    conflict_id: Optional[str] = None,
    conflict_type: str = "implementation_approach",
    agents_involved: Optional[List[str]] = None,
    proposals: Optional[List[AgentProposal]] = None,
    task_id: Optional[str] = None,
) -> Conflict:
    """Create a sample Conflict for testing.

    Args:
        conflict_id: Unique conflict identifier
        conflict_type: Type of conflict
        agents_involved: List of agents in conflict
        proposals: List of competing proposals
        task_id: Associated task ID

    Returns:
        A Conflict instance with the specified or default values
    """
    if proposals is None:
        proposals = [
            create_sample_agent_proposal(agent="backend"),
            create_sample_agent_proposal(
                agent="architect",
                proposal="Use service layer abstraction",
                reasoning="Better separation of concerns",
            ),
        ]

    return Conflict(
        conflict_id=conflict_id or f"conflict_{uuid.uuid4().hex[:8]}",
        conflict_type=conflict_type,
        agents_involved=agents_involved or ["backend", "architect"],
        proposals=proposals,
        task_id=task_id or f"task_{uuid.uuid4().hex[:8]}",
    )


def create_sample_decision(
    conflict_id: Optional[str] = None,
    chosen_agent: str = "backend",
    chosen_proposal: str = "Implement feature using factory pattern",
    reasoning: str = "Factory pattern aligns with existing codebase patterns",
    timestamp: Optional[datetime] = None,
    override_conditions: Optional[str] = None,
) -> Decision:
    """Create a sample Decision for testing.

    Args:
        conflict_id: ID of the resolved conflict
        chosen_agent: Agent whose proposal was selected
        chosen_proposal: The selected proposal text
        reasoning: Justification for the decision
        timestamp: When decision was made
        override_conditions: Conditions under which to reconsider

    Returns:
        A Decision instance with the specified or default values
    """
    return Decision(
        conflict_id=conflict_id or f"conflict_{uuid.uuid4().hex[:8]}",
        chosen_agent=chosen_agent,
        chosen_proposal=chosen_proposal,
        reasoning=reasoning,
        timestamp=timestamp or datetime.now(),
        override_conditions=override_conditions,
    )


def create_sample_quality_check(
    passed: bool = True,
    score: float = 0.85,
    checks: Optional[Dict[str, bool]] = None,
    reason: Optional[str] = None,
) -> QualityCheck:
    """Create a sample QualityCheck for testing.

    Args:
        passed: Whether quality check passed
        score: Quality score (0.0-1.0)
        checks: Dictionary of individual check results
        reason: Explanation for the result

    Returns:
        A QualityCheck instance with the specified or default values
    """
    return QualityCheck(
        passed=passed,
        score=score,
        checks=checks or {
            "syntax_valid": True,
            "tests_pass": True,
            "no_security_issues": True,
        },
        reason=reason,
    )


def create_sample_agent_metrics(
    agent_type: str = "backend",
    tasks_completed: int = 50,
    tasks_failed: int = 5,
    avg_quality_score: float = 0.87,
    avg_execution_time_ms: int = 2500,
    success_rate: Optional[float] = None,
    last_updated: Optional[datetime] = None,
) -> AgentMetrics:
    """Create a sample AgentMetrics for testing.

    Args:
        agent_type: Type of agent
        tasks_completed: Number of completed tasks
        tasks_failed: Number of failed tasks
        avg_quality_score: Average quality score
        avg_execution_time_ms: Average execution time
        success_rate: Success rate (calculated if not provided)
        last_updated: Last update timestamp

    Returns:
        An AgentMetrics instance with the specified or default values
    """
    if success_rate is None:
        total = tasks_completed + tasks_failed
        success_rate = tasks_completed / total if total > 0 else 0.0

    return AgentMetrics(
        agent_type=agent_type,
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
        avg_quality_score=avg_quality_score,
        avg_execution_time_ms=avg_execution_time_ms,
        success_rate=success_rate,
        last_updated=last_updated or datetime.now(),
    )


def create_sample_tool_result(
    success: bool = True,
    output: str = "Tool executed successfully",
    error: Optional[str] = None,
    execution_time_ms: int = 500,
    tool_used: Optional[str] = "test_tool",
    artifacts: Optional[List[str]] = None,
) -> ToolResult:
    """Create a sample ToolResult for testing.

    Args:
        success: Whether tool execution succeeded
        output: Tool output text
        error: Error message if failed
        execution_time_ms: Execution time in milliseconds
        tool_used: Name of tool used
        artifacts: List of artifact paths created

    Returns:
        A ToolResult instance with the specified or default values
    """
    return ToolResult(
        success=success,
        output=output,
        error=error,
        execution_time_ms=execution_time_ms,
        tool_used=tool_used,
        artifacts=artifacts or [],
    )


def create_sample_project_spec(
    goal: str = "Build a REST API with authentication",
    components: Optional[List[str]] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    architecture: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> ProjectSpec:
    """Create a sample ProjectSpec for testing.

    Args:
        goal: Project goal description
        components: List of component names
        tasks: List of task definitions
        architecture: Architecture specification
        created_at: Creation timestamp

    Returns:
        A ProjectSpec instance with the specified or default values
    """
    return ProjectSpec(
        goal=goal,
        components=components or ["api", "auth", "database"],
        tasks=tasks or [
            {"id": "task_001", "description": "Setup project structure"},
            {"id": "task_002", "description": "Implement authentication"},
        ],
        architecture=architecture or {
            "type": "microservice",
            "database": "postgresql",
            "auth": "jwt",
        },
        created_at=created_at or datetime.now(),
    )


def create_task_batch(
    count: int = 5,
    agent_type: Optional[AgentType] = None,
    status: Optional[TaskStatus] = None,
    with_dependencies: bool = False,
) -> List[Task]:
    """Create a batch of sample tasks for testing.

    Args:
        count: Number of tasks to create
        agent_type: If provided, all tasks will have this type
        status: If provided, all tasks will have this status
        with_dependencies: If True, create sequential dependencies

    Returns:
        A list of Task instances
    """
    agent_types = list(AgentType)
    tasks = []

    for i in range(count):
        task_id = f"batch_task_{i:03d}"

        # Cycle through agent types if not specified
        task_agent_type = agent_type or agent_types[i % len(agent_types)]
        task_status = status or TaskStatus.PENDING

        # Add dependency on previous task if requested
        dependencies = []
        if with_dependencies and i > 0:
            dependencies = [f"batch_task_{i-1:03d}"]

        task = create_sample_task(
            task_id=task_id,
            description=f"Batch test task {i + 1}",
            agent_type=task_agent_type,
            status=task_status,
            dependencies=dependencies,
        )
        tasks.append(task)

    return tasks
