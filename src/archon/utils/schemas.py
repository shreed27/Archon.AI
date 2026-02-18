"""
Pydantic schemas for ARCHON data structures.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    NEEDS_DELIBERATION = "needs_deliberation"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Available agent types."""

    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    SECURITY = "security"
    TESTING = "testing"
    INTEGRATION = "integration"
    DOCUMENTATION = "documentation"
    GIT = "git"
    DATABASE = "database"
    PERFORMANCE = "performance"
    DATA = "data"
    ARCHITECT = "architect"


class Task(BaseModel):
    """Task definition."""

    task_id: str
    description: str
    agent_type: AgentType
    model_assigned: Optional[str] = None
    tool_assigned: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = Field(default_factory=list)
    quality_threshold: float = 0.8
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class FileChange(BaseModel):
    """File modification record."""

    path: str
    change_type: str  # "create", "modify", "delete"
    lines_added: int = 0
    lines_removed: int = 0
    agent: str


class TaskResult(BaseModel):
    """Result of task execution."""

    task_id: Optional[str] = None
    success: bool
    output: Any  # Can be dict or string
    files_modified: List[FileChange] = Field(default_factory=list)
    quality_score: float
    execution_time_ms: int
    model_used: Optional[str] = None
    tool_used: Optional[str] = None
    needs_deliberation: bool = False
    architecture_changes: Optional[Dict] = None
    error: Optional[str] = None


class QualityCheck(BaseModel):
    """Quality gate validation result."""

    passed: bool
    score: float
    checks: Dict[str, bool]
    reason: Optional[str] = None


class AgentProposal(BaseModel):
    """Agent proposal during deliberation."""

    agent: str
    proposal: str
    reasoning: str
    risk_score: float
    complexity_score: float
    estimated_time_hours: float


class Conflict(BaseModel):
    """Conflict requiring deliberation."""

    conflict_id: str
    conflict_type: str
    agents_involved: List[str]
    proposals: List[AgentProposal]
    task_id: str


class Decision(BaseModel):
    """Manager decision on conflict."""

    conflict_id: str
    chosen_agent: str
    chosen_proposal: str
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.now)
    override_conditions: Optional[str] = None


class ProjectSpec(BaseModel):
    """Project specification."""

    goal: str
    components: List[str]
    tasks: List[Dict[str, Any]]
    architecture: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.now)


class ToolUsageLog(BaseModel):
    """External tool usage log."""

    task_id: str
    tool_name: str
    success: bool
    execution_time_ms: int
    input_hash: str
    output_hash: str
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentMetrics(BaseModel):
    """Agent performance metrics."""

    agent_type: str
    tasks_completed: int
    tasks_failed: int
    avg_quality_score: float
    avg_execution_time_ms: int
    success_rate: float
    last_updated: datetime = Field(default_factory=datetime.now)


class ToolResult(BaseModel):
    """Result from external tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    execution_time_ms: int
    tool_used: Optional[str] = None
    artifacts: List[str] = Field(default_factory=list)


class Tool(BaseModel):
    """External tool definition."""

    name: str
    description: str
    trust_score: float
    task_types_supported: List[str] = Field(default_factory=list)
