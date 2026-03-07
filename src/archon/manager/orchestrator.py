"""
Manager Orchestrator - The central intelligence of ARCHON.

The Manager NEVER writes code directly.
The Manager ONLY orchestrates, routes, arbitrates, and validates.
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

from archon.models.model_router import ModelRouter
from archon.manager.tool_router import ToolRouter
from archon.tools.sandbox import ToolSandbox
from archon.tools.eraser import EraserCLITool
from archon.manager.task_scheduler import TaskScheduler
from archon.manager.arbitrator import Arbitrator
from archon.manager.quality_gate import QualityGate
from archon.manager.learning_engine import LearningEngine
from archon.manager.file_writer import FileWriter
from archon.persistence.database import Database
from archon.persistence.task_graph import TaskGraph
from archon.persistence.architecture_state import ArchitectureState
from archon.persistence.s3_storage import S3Storage
from archon.utils.schemas import Task, TaskStatus, TaskResult
from archon.utils.logger import get_logger
from archon.manager.structure_planner import ProjectStructurePlanner
from archon.manager.intent_router import IntentRouter, Intent
from archon.manager.project_planner import ProjectPlanner

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
        self.sandbox = ToolSandbox(str(self.project_path))
        self.learning_engine = LearningEngine()
        self.model_router = ModelRouter()
        self.tool_router = ToolRouter(self.sandbox, self.learning_engine)

        # Persistence & Storage
        self.s3_storage = S3Storage()
        self.db: Optional[Database] = None
        self.task_graph: Optional[TaskGraph] = None
        self.architecture_state: Optional[ArchitectureState] = None

        # Tools
        self.tool_router.register_tool(
            EraserCLITool(
                self.sandbox, s3_storage=self.s3_storage, project_id=self.project_path.name
            )
        )

        self.task_scheduler = TaskScheduler()
        self.arbitrator = Arbitrator()
        self.quality_gate = QualityGate(str(self.project_path))

        self.file_ownership_map: Dict[str, str] = {}
        self.file_writer = FileWriter(str(self.project_path))
        self.structure_planner = ProjectStructurePlanner(
            str(self.project_path), model_router=self.model_router
        )
        self.intent_router = IntentRouter()
        self.project_planner = ProjectPlanner(model_router=self.model_router)

        from archon.intelligence.code_retriever import CodeRetriever

        self.code_retriever = CodeRetriever(str(self.project_path))
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

        # Initialize quality gate with full context
        self.quality_gate = QualityGate(str(self.project_path), self.architecture_state)

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
        Parse user goal into structured specification using ProjectPlanner.
        """
        logger.info(f"Parsing goal: {goal}")

        project_context = ""
        archon_md_path = self.project_path / ".archon.md"
        if archon_md_path.exists():
            with open(archon_md_path, "r", encoding="utf-8") as f:
                project_context = f"\n\nProject Directives (.archon.md):\n{f.read()}"

        spec = await self.project_planner.generate_spec(goal, project_context)

        # Store specification
        await self.db.store_specification(spec)

        return spec

    async def execute_plan(self, spec: Dict) -> AsyncGenerator[Dict, None]:
        """
        Execute the plan with live progress updates.

        Yields progress updates as tasks are executed.
        """
        import time
        from archon.manager.project_memory import ProjectMemory

        self.project_memory = ProjectMemory()

        # Validation: Prevent execution with empty tasks
        tasks_to_check = spec.get("tasks", [])
        if len(tasks_to_check) == 0:
            logger.warning("Planner produced no tasks. Using fallback plan.")
            print("Planner produced no tasks. Using fallback plan.")
            fallback_spec = self.project_planner.fallback_plan(spec.get("goal", "current project"))
            spec.update(fallback_spec)

        # Stats tracking
        start_time = time.time()
        stats = {
            "tasks_executed": 0,
            "agents_involved": set(),
            "files_created": 0,
            "conflicts_resolved": 0,
        }

        # Clear ownership map for the new execution plan
        self.file_ownership_map.clear()

        # Step 1: Run Structure Planner
        project_structure = await self.structure_planner.generate_structure(spec)
        self.structure_planner.create_directories(project_structure)

        # Update ProjectMemory's codebase_index
        if project_structure:
            self.project_memory.codebase_index.initial_structure = project_structure
            yield {"type": "structure_planned", "structure": project_structure}

        # Create task DAG
        tasks = await self.task_scheduler.create_task_dag(spec)
        await self.task_graph.store_tasks(tasks)

        # Execute tasks in dependency order
        while True:
            executable_tasks = await self.task_scheduler.get_executable_tasks(tasks)

            if not executable_tasks:
                break

            # Yield task_started before execution
            for task in executable_tasks:
                agent_name = (
                    str(task.agent_type.value)
                    if hasattr(task.agent_type, "value")
                    else str(task.agent_type)
                )
                stats["agents_involved"].add(agent_name)
                yield {
                    "type": "task_started",
                    "task_id": task.task_id,
                    "agent": agent_name,
                    "description": task.description,
                }

            # Execute tasks in parallel where possible
            results = await asyncio.gather(
                *[self._execute_task(task) for task in executable_tasks], return_exceptions=True
            )

            # Yield progress updates
            for task, result in zip(executable_tasks, results):
                if isinstance(result, Exception):
                    yield {"type": "task_failed", "task_id": task.task_id, "error": str(result)}
                else:
                    stats["tasks_executed"] += 1

                    if hasattr(result, "files_created") and result.files_created:
                        for path in result.files_created:
                            stats["files_created"] += 1
                            yield {"type": "file_created", "path": path}

                    if hasattr(result, "file_conflicts") and result.file_conflicts:
                        for conflict in result.file_conflicts:
                            stats["conflicts_resolved"] += 1
                            yield {
                                "type": "conflict_resolved",
                                "file": conflict["path"],
                                "owner": conflict["owner"],
                                "attempted": conflict["attempted_by"],
                                "winner": conflict.get("winner", conflict["owner"]),
                            }

                    agent_name = (
                        str(task.agent_type.value)
                        if hasattr(task.agent_type, "value")
                        else str(task.agent_type)
                    )
                    yield {
                        "type": "task_completed",
                        "task_id": task.task_id,
                        "agent": agent_name,
                        "description": task.description,
                    }

        execution_time = int(time.time() - start_time)
        logger.info("Plan execution complete")

        # Yield final summary
        summary_lines = [
            "## Execution Summary\n",
            f"Tasks executed: {stats['tasks_executed']}",
            f"Agents involved: {', '.join(sorted(stats['agents_involved'])) if stats['agents_involved'] else 'None'}",
            f"Files created: {stats['files_created']}",
            f"Conflicts resolved: {stats['conflicts_resolved']}",
            f"Execution time: {execution_time}s",
        ]

        yield {"type": "execution_summary", "summary": "\n".join(summary_lines)}

    async def plan_feature(self, feature_description: str) -> Dict:
        """
        Uses FeaturePlanner to generate tasks to add a new feature to an existing project.
        """
        if not self.initialized:
            await self.load_state()

        from archon.manager.feature_planner import FeaturePlanner
        from archon.manager.project_memory import ProjectMemory

        if not hasattr(self, "project_memory"):
            self.project_memory = ProjectMemory()

        code_retriever = getattr(self, "code_retriever", None)
        self.feature_planner = FeaturePlanner(
            str(self.project_path), self.code_retriever, model_router=self.model_router
        )

        spec = await self.feature_planner.generate_feature_plan(
            feature_description, self.project_memory.codebase_index, self.project_memory
        )

        await self.db.store_specification(spec)
        return spec

    async def execute_feature_plan(self, spec: Dict) -> AsyncGenerator[Dict, None]:
        """
        Execute tasks related to a new feature modifying existing codebase.
        Skips StructurePlanner and preserves existing ProjectMemory.
        """
        import time
        from archon.manager.project_memory import ProjectMemory

        logger.info("Starting feature execution")

        if not hasattr(self, "project_memory"):
            self.project_memory = ProjectMemory()

        # Stats tracking
        start_time = time.time()
        stats = {
            "tasks_executed": 0,
            "agents_involved": set(),
            "files_modified": 0,
            "conflicts_resolved": 0,
        }

        # Clear ownership map for the new execution plan
        self.file_ownership_map.clear()

        # Generate Task DAG
        tasks = await self.task_scheduler.create_task_dag(spec)
        await self.task_graph.store_tasks(tasks)

        while True:
            executable_tasks = await self.task_scheduler.get_executable_tasks(tasks)
            if not executable_tasks:
                break

            for task in executable_tasks:
                agent_name = (
                    str(task.agent_type.value)
                    if hasattr(task.agent_type, "value")
                    else str(task.agent_type)
                )
                stats["agents_involved"].add(agent_name)
                yield {
                    "type": "task_started",
                    "task_id": task.task_id,
                    "agent": agent_name,
                    "description": task.description,
                }

            results = await asyncio.gather(
                *[self._execute_task(task) for task in executable_tasks], return_exceptions=True
            )

            for task, result in zip(executable_tasks, results):
                if isinstance(result, Exception):
                    yield {"type": "task_failed", "task_id": task.task_id, "error": str(result)}
                else:
                    stats["tasks_executed"] += 1

                    if hasattr(result, "files_created") and result.files_created:
                        for path in result.files_created:
                            stats["files_modified"] += 1
                            yield {"type": "file_created", "path": path}

                    if hasattr(result, "file_conflicts") and result.file_conflicts:
                        for conflict in result.file_conflicts:
                            stats["conflicts_resolved"] += 1
                            yield {
                                "type": "conflict_resolved",
                                "file": conflict["path"],
                                "owner": conflict["owner"],
                                "attempted": conflict["attempted_by"],
                                "winner": conflict.get("winner", conflict["owner"]),
                            }

                    agent_name = (
                        str(task.agent_type.value)
                        if hasattr(task.agent_type, "value")
                        else str(task.agent_type)
                    )
                    yield {
                        "type": "task_completed",
                        "task_id": task.task_id,
                        "agent": agent_name,
                        "description": task.description,
                    }

        execution_time = int(time.time() - start_time)
        logger.info("Feature execution complete")

        summary_lines = [
            "## Feature Execution Summary\n",
            f"Tasks executed: {stats['tasks_executed']}",
            f"Agents involved: {', '.join(sorted(stats['agents_involved'])) if stats['agents_involved'] else 'None'}",
            f"Files modified: {stats['files_modified']}",
            f"Conflicts resolved: {stats['conflicts_resolved']}",
            f"Execution time: {execution_time}s",
        ]

        yield {"type": "execution_summary", "summary": "\n".join(summary_lines)}

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
        tool_name = await self.tool_router.select_best_tool(task)

        if tool_name:
            logger.info(f"Using external tool: {tool_name}")
            result = await self._execute_with_tool(task, tool_name)
        else:
            # All agents now respect the global configuration from ModelRouter.
            # We pass a placeholder value; agents will use ModelRouter.generate() internally.
            result = await self._execute_with_agent(task, "selected-model")

        # Quality gate
        quality_check = await self.quality_gate.validate(result)

        if not quality_check.passed:
            logger.warning(f"Quality gate failed: {quality_check.reason}")
            task.status = TaskStatus.FAILED
            await self.db.update_task_status(task.task_id, TaskStatus.FAILED)
            raise ValueError(f"Quality gate failed: {quality_check.reason}")

        # Commit files to disk
        created_files = self.file_writer.write_artifacts(
            result,
            task.agent_type.value if hasattr(task.agent_type, "value") else str(task.agent_type),
            self.file_ownership_map,
            getattr(self, "project_memory", None),
        )
        result.files_created = created_files

        if hasattr(self, "project_memory"):
            for path in created_files:
                self.project_memory.files_created.append(path)

        # Handle file conflicts: print them out and let Arbitrator decide
        if hasattr(result, "file_conflicts") and result.file_conflicts:
            from archon.utils.schemas import AgentProposal

            for conflict in result.file_conflicts:
                # We mock Agent Proposals for the file contents
                p1 = AgentProposal(
                    agent=conflict["owner"],
                    proposal=conflict.get("original_content", ""),
                    reasoning=f"Original version authored by {conflict['owner']}.",
                    risk_score=0.1,
                    complexity_score=0.5,
                    estimated_time_hours=0.0,
                )
                p2 = AgentProposal(
                    agent=conflict["attempted_by"],
                    proposal=conflict.get("attempted_content", ""),
                    reasoning=f"New version proposed by {conflict['attempted_by']}.",
                    risk_score=0.2,  # slightly riskier to overwrite
                    complexity_score=0.5,
                    estimated_time_hours=0.0,
                )

                decision = await self.arbitrator.resolve_conflict(task, [p1, p2])
                winner_agent = decision.chosen_agent
                conflict["winner"] = winner_agent

                # Write the selected version
                try:
                    with open(conflict["target_path"], "w", encoding="utf-8") as f:
                        f.write(decision.chosen_proposal)
                    # Update ownership map
                    self.file_ownership_map[conflict["path"]] = winner_agent
                except Exception as e:
                    logger.error(f"Failed to write arbitrated file {conflict['path']}: {e}")

        # Update state
        await self._update_project_state(task, result)

        # Learn
        await self.learning_engine.record_outcome(task, result)

        task.status = TaskStatus.COMPLETED
        await self.db.update_task_status(task.task_id, TaskStatus.COMPLETED)

        return result

    async def _execute_with_tool(self, task: Task, tool_name: str) -> TaskResult:
        """Execute task using external CLI tool."""

        # Prepare input data from task context or description
        input_data = task.context or {}
        if not input_data and "dsl" not in input_data:
            # Basic fallback: pass description as potential DSL if relevant
            input_data["dsl"] = task.description

        result = await self.tool_router.execute_tool(tool_name, input_data)

        # Log tool usage
        if self.db:
            await self.db.log_tool_usage(
                {
                    "task_id": task.task_id,
                    "tool": tool_name,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "timestamp": datetime.now(),
                }
            )

        return TaskResult(
            success=result.success,
            output=result.output or result.error,
            execution_time_ms=result.execution_time_ms,
            tool_used=tool_name,
            quality_score=0.9 if result.success else 0.0,
            model_used=None,
        )

    async def _execute_with_agent(self, task: Task, model) -> TaskResult:
        """Execute task using AI agent."""

        from archon.agents import get_agent

        agent = get_agent(task.agent_type)

        if hasattr(self, "code_retriever"):
            try:
                relevant_files = self.code_retriever.search(task.description, top_k=3)
                if relevant_files:
                    snippet_text = "\n\nRelevant project files:\n\n"
                    for f in relevant_files:
                        snippet_text += f"{f['path']}\n```\n{f['content']}\n```\n\n"
                    task.description += snippet_text
            except Exception as e:
                logger.error(f"Error retrieving relevant files: {e}")

        # Inject Patch instructions for existing projects/features
        from archon.intelligence.patch_generator import PatchGenerator

        patch_instructions = PatchGenerator.get_patch_prompt_instructions()
        task.description += f"\n\n{patch_instructions}"

        result = await agent.execute(
            task, model, project_memory=getattr(self, "project_memory", None)
        )

        # Check for conflicts
        if result.needs_deliberation:
            logger.info("Deliberation needed")
            result = await self.arbitrator.resolve_conflict(task, result)

        return result

    async def _update_project_state(self, task: Task, result: TaskResult):
        """Update global project state after task completion."""

        # Update file ownership and upload artifacts to S3
        if isinstance(result.output, dict) and "artifact_urls" not in result.output:
            result.output["artifact_urls"] = []

        for file_change in result.files_modified:
            await self.db.update_file_ownership(file_change.path, task.agent_type, datetime.now())

            # Find content in result if available
            content = None
            if isinstance(result.output, dict) and "files" in result.output:
                for f in result.output["files"]:
                    if f.get("path") == file_change.path:
                        content = f.get("content")
                        break

            if content:
                # Upload to S3 instead of local container filesystem
                from pathlib import Path

                url = await self.s3_storage.upload_content(
                    content=content,
                    project_id=self.project_path.name,
                    file_name=Path(file_change.path).name,
                )
                if url:
                    logger.info(f"Artifact {file_change.path} uploaded to S3: {url}")
                    if isinstance(result.output, dict):
                        result.output["artifact_urls"].append(url)

        # Update architecture state
        if result.architecture_changes:
            await self.architecture_state.apply_changes(result.architecture_changes)

        # Update ProjectMemory
        if hasattr(self, "project_memory") and isinstance(result.output, dict):
            # Endpoints
            endpoints = result.output.get("endpoints", []) or result.output.get("api_endpoints", [])
            if isinstance(endpoints, list):
                self.project_memory.endpoints.extend(endpoints)

            # Schemas
            schemas = result.output.get("schemas", {}) or result.output.get("database_changes", {})
            if isinstance(schemas, dict):
                self.project_memory.schemas.update(schemas)
            elif isinstance(schemas, list) and schemas:
                # If database_changes is a list of changes
                self.project_memory.schemas[task.task_id] = schemas

            # Architecture
            if "architecture" in result.output and isinstance(result.output["architecture"], dict):
                self.project_memory.architecture.update(result.output["architecture"])

            # Notes
            notes = result.output.get("notes") or result.output.get("agent_notes")
            if notes:
                agent_name = (
                    task.agent_type.value
                    if hasattr(task.agent_type, "value")
                    else str(task.agent_type)
                )
                self.project_memory.agent_notes[agent_name] = notes

    async def get_status(self) -> Dict:
        """Get current project status."""

        return {
            "project_name": self.project_path.name,
            "status": "active",
            "tasks_total": await self.db.count_tasks() if self.db else 0,
            "tasks_completed": (
                await self.db.count_tasks_by_status(TaskStatus.COMPLETED) if self.db else 0
            ),
            "active_tasks": await self.db.get_active_tasks() if self.db else [],
            "agent_metrics": await self.db.get_agent_metrics() if self.db else {},
        }

    async def show_status(self) -> str:
        """Format project status as a string for conversational interaction."""
        if not self.initialized:
            try:
                await self.load_state()
            except Exception:
                return "The project has not been initialized yet. Use 'create project' to start."

        status = await self.get_status()

        msg = f"## Project Status: {status['project_name']}\n"
        msg += f"- **Current State:** {status['status'].capitalize()}\n"
        msg += f"- **Task Progress:** {status['tasks_completed']}/{status['tasks_total']} tasks completed.\n"

        if status["active_tasks"]:
            msg += "\n### Active Tasks:\n"
            for task in status["active_tasks"]:
                msg += f"- {task['agent']} is currently {task['status']}: {task['description']}\n"

        return msg

    async def process_conversational_input(
        self, user_input: str, history: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Process conversational input from user using IntentRouter (non-streaming).
        """
        history = history or []
        router_response = await self.intent_router.route(user_input, history)
        intent = router_response.intent
        message = router_response.message
        metadata = router_response.metadata

        result = {"action": None, "message": message, "spec": None}

        if intent == Intent.CREATE_PROJECT:
            goal = metadata.get("goal", user_input)
            spec = await self.parse_goal_to_spec(goal)
            result["action"] = "execute_task"
            result["spec"] = spec
            result["message"] = f"{message}\n\n{self.format_plan_summary(spec)}"

        elif intent == Intent.ADD_FEATURE or intent == Intent.MODIFY_CODE:
            feature = metadata.get("feature") or metadata.get("modification") or user_input
            spec = await self.plan_feature(feature)
            result["action"] = "execute_task"
            result["spec"] = spec
            result["message"] = f"{message}\n\n{self.format_plan_summary(spec)}"

        elif intent == Intent.PROJECT_STATUS:
            status_msg = await self.show_status()
            result["action"] = "show_status"
            result["message"] = f"{message}\n\n{status_msg}"

        elif intent == Intent.CHAT:
            result["action"] = "chat"
            result["message"] = message

        return result

    async def stream_conversational_input(
        self, user_input: str, history: Optional[List[Dict]] = None
    ):
        """
        Process conversational input and yield response in chunks.
        """
        history = history or []

        # Intent detection (can't stream this easily as it needs structured JSON)
        router_response = await self.intent_router.route(user_input, history)
        intent = router_response.intent
        message = router_response.message
        metadata = router_response.metadata

        if intent == Intent.CHAT:
            # For pure chat, we can stream the LLM response directly
            async for chunk in self.model_router.stream_generate(history):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "done", "action": "chat"}

        elif intent == Intent.CREATE_PROJECT:
            yield {"type": "chunk", "content": message + "\n\n"}
            goal = metadata.get("goal", user_input)
            spec = await self.parse_goal_to_spec(goal)
            yield {"type": "chunk", "content": self.format_plan_summary(spec)}
            yield {"type": "done", "action": "execute_task", "spec": spec}

        elif intent in (Intent.ADD_FEATURE, Intent.MODIFY_CODE):
            yield {"type": "chunk", "content": message + "\n\n"}
            feature = metadata.get("feature") or metadata.get("modification") or user_input
            spec = await self.plan_feature(feature)
            yield {"type": "chunk", "content": self.format_plan_summary(spec)}
            yield {"type": "done", "action": "execute_task", "spec": spec}

        else:
            # Fallback for other intents
            result = await self.process_conversational_input(user_input, history)
            yield {"type": "chunk", "content": result.get("message", "")}
            yield {
                "type": "done",
                "action": result.get("action"),
                "spec": result.get("spec"),
                "message": result.get("message"),
            }

    def format_plan_summary(self, spec: Dict) -> str:
        """Format the execution plan summary for the user."""
        goal = spec.get("goal", "Unknown goal")
        tasks = spec.get("tasks", [])
        total_tasks = len(tasks)

        agents_used = set()
        for t in tasks:
            agent = t.get("agent", "UnknownAgent")
            agents_used.add(agent)

        agents_str = "\n".join([f"- {a}" for a in sorted(agents_used)])

        lines = [
            f"Goal: {goal}\n",
            "## Plan Summary\n",
            f"Total Tasks: {total_tasks}",
            "Agents involved:",
            f"{agents_str}\n",
        ]

        if tasks:
            for i, t in enumerate(tasks, start=1):
                agent = t.get("agent", "UnknownAgent")
                desc = t.get("description", "")
                lines.append(f"{i}. {agent}")
                lines.append(f"   {desc}\n")

        return "\n".join(lines).strip()
