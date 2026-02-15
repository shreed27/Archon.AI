"""
Manager Orchestrator - The central intelligence of ARCHON.

The Manager NEVER writes code directly.
The Manager ONLY orchestrates, routes, arbitrates, and validates.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

from archon.manager.model_router import ModelRouter
from archon.manager.tool_router import ToolRouter
from archon.manager.task_scheduler import TaskScheduler
from archon.manager.arbitrator import Arbitrator
from archon.manager.quality_gate import QualityGate
from archon.manager.learning_engine import LearningEngine
from archon.persistence.database import Database
from archon.persistence.task_graph import TaskGraph
from archon.persistence.architecture_state import ArchitectureState
from archon.utils.schemas import Task, TaskStatus, TaskResult
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class ManagerOrchestrator:
    """
    Main Manager class - the orchestration brain of ARCHON.

    Responsibilities:
    - Maintain global project state
    - Route tasks to optimal agents/models/tools
    - Arbitrate conflicts between agents
    - Enforce quality gates
    - Learn from outcomes

    The Manager NEVER writes code directly.
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.archon_dir = self.project_path / ".archon"

        # Core subsystems
        self.model_router = ModelRouter()
        self.tool_router = ToolRouter()
        self.task_scheduler = TaskScheduler()
        self.arbitrator = Arbitrator()
        self.quality_gate = QualityGate()
        self.learning_engine = LearningEngine()

        # Persistence
        self.db: Optional[Database] = None
        self.task_graph: Optional[TaskGraph] = None
        self.architecture_state: Optional[ArchitectureState] = None

        self.initialized = False

    async def initialize(self):
        """
        Initialize Manager and create .archon directory structure.
        """

        if self.initialized:
            return

        logger.info(f"Initializing ARCHON in {self.project_path}")

        # Create .archon directory
        self.archon_dir.mkdir(exist_ok=True)
        (self.archon_dir / "agent_logs").mkdir(exist_ok=True)
        (self.archon_dir / "decisions").mkdir(exist_ok=True)
        (self.archon_dir / "sandbox").mkdir(exist_ok=True)

        # Initialize persistence layer
        self.db = Database(str(self.archon_dir / "project.db"))
        await self.db.initialize()

        self.task_graph = TaskGraph(str(self.archon_dir / "task_graph.json"))
        await self.task_graph.initialize()

        self.architecture_state = ArchitectureState(str(self.archon_dir / "architecture_map.json"))
        await self.architecture_state.initialize()

        # Initialize learning engine
        await self.learning_engine.initialize(self.archon_dir)

        self.initialized = True
        logger.info("ARCHON initialized successfully")

    async def load_state(self):
        """
        Load existing ARCHON state from .archon directory.
        """

        if not self.archon_dir.exists():
            raise ValueError(f"No ARCHON session found in {self.project_path}")

        await self.initialize()
        logger.info("ARCHON state loaded")

    async def parse_goal_to_spec(self, goal: str) -> Dict:
        """
        Parse user goal into structured specification.

        Uses AI to understand goal and create structured plan.

        Returns:
            {
                "goal": str,
                "components": List[str],
                "tasks": List[Dict],
                "architecture": Dict
            }
        """

        logger.info(f"Parsing goal: {goal}")

        # Use GPT-4 for goal understanding (high reasoning task)
        from archon.models.openai_client import OpenAIClient

        client = OpenAIClient()

        prompt = f"""
You are the Manager of ARCHON, an AI engineering organization.

User Goal: {goal}

Parse this goal into a structured specification with:
1. Clear goal statement
2. List of components needed
3. Breakdown into tasks with agent assignments
4. Initial architecture design

Return JSON format:
{{
    "goal": "...",
    "components": ["backend", "frontend", ...],
    "tasks": [
        {{
            "id": "task_001",
            "description": "...",
            "agent": "backend",
            "dependencies": []
        }}
    ],
    "architecture": {{
        "type": "monolith" | "microservices",
        "databases": [...],
        "apis": [...]
    }}
}}
"""

        response = await client.complete(prompt, model="gpt-4-turbo")
        spec = response["parsed_json"]

        # Store specification
        await self.db.store_specification(spec)

        return spec

    async def execute_plan(self, spec: Dict) -> AsyncGenerator[Dict, None]:
        """
        Execute the plan with live progress updates.

        Yields progress updates as tasks are executed.
        """

        logger.info("Starting plan execution")

        # Create task DAG
        tasks = await self.task_scheduler.create_task_dag(spec)
        await self.task_graph.store_tasks(tasks)

        # Execute tasks in dependency order
        while True:
            executable_tasks = await self.task_scheduler.get_executable_tasks(tasks)

            if not executable_tasks:
                break

            # Execute tasks in parallel where possible
            results = await asyncio.gather(
                *[self._execute_task(task) for task in executable_tasks], return_exceptions=True
            )

            # Yield progress updates
            for task, result in zip(executable_tasks, results):
                if isinstance(result, Exception):
                    yield {"type": "task_failed", "task_id": task.task_id, "error": str(result)}
                else:
                    yield {
                        "type": "task_completed",
                        "task_id": task.task_id,
                        "agent": task.agent_type,
                        "description": task.description,
                    }

        logger.info("Plan execution complete")

    async def _execute_task(self, task: Task) -> TaskResult:
        """
        Execute a single task by routing to optimal executor.

        Decision flow:
        1. Should we use external tool or AI model?
        2. If AI, which model?
        3. Execute
        4. Validate quality
        5. Update state
        """

        logger.info(f"Executing task {task.task_id}: {task.description}")

        # Update task status
        task.status = TaskStatus.IN_PROGRESS
        await self.db.update_task_status(task.task_id, TaskStatus.IN_PROGRESS)

        # Decision: Tool vs AI
        tool_decision = await self.tool_router.should_use_tool(task)

        if tool_decision.use_tool:
            logger.info(f"Using external tool: {tool_decision.tool.name}")
            result = await self._execute_with_tool(task, tool_decision.tool)
        else:
            # Select optimal model
            model = await self.model_router.select_model(task)
            logger.info(f"Using AI model: {model.value}")
            result = await self._execute_with_agent(task, model)

        # Quality gate
        quality_check = await self.quality_gate.validate(result)

        if not quality_check.passed:
            logger.warning(f"Quality gate failed: {quality_check.reason}")
            task.status = TaskStatus.FAILED
            await self.db.update_task_status(task.task_id, TaskStatus.FAILED)
            raise ValueError(f"Quality gate failed: {quality_check.reason}")

        # Update state
        await self._update_project_state(task, result)

        # Learn
        await self.learning_engine.record_outcome(task, result)

        task.status = TaskStatus.COMPLETED
        await self.db.update_task_status(task.task_id, TaskStatus.COMPLETED)

        return result

    async def _execute_with_tool(self, task: Task, tool) -> TaskResult:
        """Execute task using external CLI tool."""

        from archon.tools.tool_sandbox import ToolSandbox

        sandbox = ToolSandbox(self.archon_dir / "sandbox")
        result = await sandbox.execute(tool, task.context)

        # Log tool usage
        await self.db.log_tool_usage(
            {
                "task_id": task.task_id,
                "tool": tool.name,
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "timestamp": datetime.now(),
            }
        )

        return result

    async def _execute_with_agent(self, task: Task, model) -> TaskResult:
        """Execute task using AI agent."""

        from archon.agents import get_agent

        agent = get_agent(task.agent_type)
        result = await agent.execute(task, model)

        # Check for conflicts
        if result.needs_deliberation:
            logger.info("Deliberation needed")
            result = await self.arbitrator.resolve_conflict(task, result)

        return result

    async def _update_project_state(self, task: Task, result: TaskResult):
        """Update global project state after task completion."""

        # Update file ownership
        for file_change in result.files_modified:
            await self.db.update_file_ownership(file_change.path, task.agent_type, datetime.now())

        # Update architecture state
        if result.architecture_changes:
            await self.architecture_state.apply_changes(result.architecture_changes)

    async def get_status(self) -> Dict:
        """Get current project status."""

        return {
            "project_name": self.project_path.name,
            "status": "active",
            "tasks_total": await self.db.count_tasks(),
            "tasks_completed": await self.db.count_tasks_by_status(TaskStatus.COMPLETED),
            "active_tasks": await self.db.get_active_tasks(),
            "agent_metrics": await self.db.get_agent_metrics(),
        }

    async def process_conversational_input(self, user_input: str, history: List[Dict]) -> Dict:
        """
        Process conversational input from user.

        Uses AI to understand intent and determine action.
        """

        from archon.models.openai_client import OpenAIClient

        client = OpenAIClient()

        prompt = f"""
You are the Manager of ARCHON. The user said: "{user_input}"

Conversation history: {history}

Determine the appropriate action:
- execute_task: User wants to add/modify functionality
- show_status: User wants project status
- modify_architecture: User wants architectural changes
- clarify: You need more information

Return JSON with action and response message.
"""

        response = await client.complete(prompt, model="gpt-4-turbo")
        return response["parsed_json"]
