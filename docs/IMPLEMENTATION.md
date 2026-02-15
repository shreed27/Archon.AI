# ARCHON Implementation Guide

## Core Modules Breakdown

### 1. Manager Orchestrator

**File**: `archon/manager/orchestrator.py`

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    NEEDS_DELIBERATION = "needs_deliberation"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    task_id: str
    description: str
    agent_type: str
    model_assigned: Optional[str]
    tool_assigned: Optional[str]
    status: TaskStatus
    dependencies: List[str]
    quality_threshold: float
    context: Dict

class ManagerOrchestrator:
    """
    Main Manager class - never writes code, only orchestrates.
    
    Responsibilities:
    - Maintain global project state
    - Route tasks to agents/models/tools
    - Arbitrate conflicts
    - Enforce quality gates
    - Learn from outcomes
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.model_router = ModelRouter()
        self.tool_router = ToolRouter()
        self.task_scheduler = TaskScheduler()
        self.arbitrator = Arbitrator()
        self.quality_gate = QualityGate()
        self.learning_engine = LearningEngine()
        
        # Load persistent state
        self.db = Database(f"{project_path}/.archon/project.db")
        self.task_graph = TaskGraph(f"{project_path}/.archon/task_graph.json")
        self.architecture_map = ArchitectureMap(f"{project_path}/.archon/architecture_map.json")
    
    async def process_user_goal(self, goal: str) -> None:
        """
        Main entry point - converts user goal into structured execution.
        
        Flow:
        1. Parse goal into specification
        2. Build project knowledge graph
        3. Create task DAG
        4. Assign tasks to agents/models/tools
        5. Execute with quality gates
        6. Learn from outcomes
        """
        
        # Step 1: Parse goal
        spec = await self._parse_goal_to_spec(goal)
        
        # Step 2: Build knowledge graph
        knowledge_graph = await self._build_knowledge_graph(spec)
        
        # Step 3: Create task DAG
        tasks = await self.task_scheduler.create_task_dag(spec, knowledge_graph)
        
        # Step 4: Execute tasks
        for task in self.task_scheduler.get_executable_tasks(tasks):
            await self._execute_task(task)
    
    async def _execute_task(self, task: Task) -> None:
        """
        Execute a single task by routing to optimal executor.
        
        Decision flow:
        1. Should we use external tool or AI model?
        2. If AI, which model?
        3. Execute
        4. Validate quality
        5. Update state
        """
        
        # Decision: Tool vs AI
        tool_decision = await self.tool_router.should_use_tool(task)
        
        if tool_decision.use_tool:
            result = await self._execute_with_tool(task, tool_decision.tool)
        else:
            # Select optimal model
            model = await self.model_router.select_model(task)
            result = await self._execute_with_agent(task, model)
        
        # Quality gate
        if not await self.quality_gate.validate(result):
            await self._handle_quality_failure(task, result)
            return
        
        # Update state
        await self._update_project_state(task, result)
        
        # Learn
        await self.learning_engine.record_outcome(task, result)
    
    async def _execute_with_tool(self, task: Task, tool: ExternalTool) -> TaskResult:
        """Execute task using external CLI tool."""
        from archon.tools.tool_sandbox import ToolSandbox
        
        sandbox = ToolSandbox()
        result = await sandbox.execute(tool, task.context)
        
        # Log tool usage
        await self.db.log_tool_usage({
            "task_id": task.task_id,
            "tool": tool.name,
            "success": result.success,
            "execution_time_ms": result.execution_time_ms
        })
        
        return result
    
    async def _execute_with_agent(self, task: Task, model: str) -> TaskResult:
        """Execute task using AI agent."""
        from archon.agents import get_agent
        
        agent = get_agent(task.agent_type)
        result = await agent.execute(task, model)
        
        # Check for conflicts
        if result.status == "needs_deliberation":
            result = await self.arbitrator.resolve_conflict(task, result)
        
        return result
```

**Key Design Decisions:**
- Manager never writes code directly
- All decisions are async and logged
- Quality gates are enforced before state updates
- Tool vs AI decision is explicit and auditable

---

### 2. Model Router

**File**: `archon/manager/model_router.py`

```python
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ModelType(Enum):
    GPT4 = "gpt-4"
    GPT4_TURBO = "gpt-4-turbo"
    CLAUDE_OPUS = "claude-opus-3"
    CLAUDE_SONNET = "claude-sonnet-3.5"
    GEMINI_PRO = "gemini-pro"
    GEMINI_FLASH = "gemini-2.0-flash"

@dataclass
class ModelSelectionCriteria:
    task_complexity: float        # 0.0 - 1.0
    reasoning_depth: float         # 0.0 - 1.0
    context_size: int              # tokens required
    speed_priority: float          # 0.0 - 1.0 (1.0 = fastest)
    cost_constraint: float         # max cost per task
    historical_performance: float  # learned metric

class ModelRouter:
    """
    Selects optimal AI model for each task.
    
    Selection based on:
    - Task characteristics
    - Model capabilities
    - Historical performance
    - Cost constraints
    """
    
    MODEL_CAPABILITIES = {
        ModelType.GPT4: {
            "max_context": 128_000,
            "reasoning_strength": 0.95,
            "speed_score": 0.6,
            "cost_per_1k_tokens": 0.03,
            "best_for": ["complex_logic", "architectural_decisions"]
        },
        ModelType.CLAUDE_OPUS: {
            "max_context": 200_000,
            "reasoning_strength": 0.93,
            "speed_score": 0.5,
            "cost_per_1k_tokens": 0.015,
            "best_for": ["security_review", "large_refactors"]
        },
        ModelType.GEMINI_FLASH: {
            "max_context": 1_000_000,
            "reasoning_strength": 0.85,
            "speed_score": 0.95,
            "cost_per_1k_tokens": 0.001,
            "best_for": ["frontend_ui", "fast_iteration"]
        }
    }
    
    async def select_model(self, task: Task) -> ModelType:
        """
        Select optimal model using multi-criteria decision analysis.
        
        Algorithm:
        1. Extract task characteristics
        2. Score each model against criteria
        3. Apply historical performance weights
        4. Return highest-scoring model
        """
        
        criteria = self._extract_criteria(task)
        scores = {}
        
        for model, capabilities in self.MODEL_CAPABILITIES.items():
            score = self._calculate_model_score(model, capabilities, criteria)
            scores[model] = score
        
        # Apply historical performance
        historical_weights = await self._get_historical_weights(task.agent_type)
        for model in scores:
            scores[model] *= historical_weights.get(model, 1.0)
        
        # Select best
        best_model = max(scores, key=scores.get)
        
        # Log decision
        await self._log_model_selection(task, best_model, scores)
        
        return best_model
    
    def _calculate_model_score(
        self, 
        model: ModelType, 
        capabilities: Dict, 
        criteria: ModelSelectionCriteria
    ) -> float:
        """
        Multi-criteria scoring function.
        
        Weighted sum of:
        - Reasoning capability match
        - Context size adequacy
        - Speed match
        - Cost efficiency
        """
        
        # Reasoning match
        reasoning_score = min(
            capabilities["reasoning_strength"] / criteria.reasoning_depth,
            1.0
        )
        
        # Context adequacy
        context_score = 1.0 if capabilities["max_context"] >= criteria.context_size else 0.5
        
        # Speed match
        speed_score = capabilities["speed_score"] * criteria.speed_priority
        
        # Cost efficiency
        cost_score = 1.0 if capabilities["cost_per_1k_tokens"] <= criteria.cost_constraint else 0.3
        
        # Weighted sum
        total_score = (
            0.4 * reasoning_score +
            0.2 * context_score +
            0.2 * speed_score +
            0.2 * cost_score
        )
        
        return total_score
```

**Key Features:**
- Multi-criteria decision analysis
- Historical performance learning
- Cost-aware selection
- Auditable decisions

---

### 3. Tool Router

**File**: `archon/manager/tool_router.py`

```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class ToolDecision:
    use_tool: bool
    tool: Optional['ExternalTool']
    reasoning: str
    confidence: float

class ToolRouter:
    """
    Decides when to use external CLI tools instead of AI models.
    
    Critical innovation: Manager can choose tools when superior.
    
    Decision criteria:
    - Capability match
    - Accuracy advantage
    - Performance history
    - Trust score
    """
    
    def __init__(self):
        from archon.tools.tool_registry import ToolRegistry
        self.registry = ToolRegistry()
    
    async def should_use_tool(self, task: Task) -> ToolDecision:
        """
        Determine if external tool is better than AI model.
        
        Algorithm:
        1. Check if any tool supports this task type
        2. Compare tool performance vs AI performance
        3. Consider trust score
        4. Return decision with reasoning
        """
        
        # Find candidate tools
        candidates = await self.registry.find_tools_for_task(task.description)
        
        if not candidates:
            return ToolDecision(
                use_tool=False,
                tool=None,
                reasoning="No suitable tools found",
                confidence=1.0
            )
        
        # Score each tool
        best_tool = None
        best_score = 0.0
        
        for tool in candidates:
            score = await self._score_tool(tool, task)
            if score > best_score:
                best_score = score
                best_tool = tool
        
        # Compare with AI baseline
        ai_baseline_score = 0.7  # Historical AI performance
        
        if best_score > ai_baseline_score * 1.2:  # 20% better threshold
            return ToolDecision(
                use_tool=True,
                tool=best_tool,
                reasoning=f"{best_tool.name} outperforms AI by {(best_score/ai_baseline_score - 1)*100:.1f}%",
                confidence=best_score
            )
        else:
            return ToolDecision(
                use_tool=False,
                tool=None,
                reasoning="AI model performance is competitive",
                confidence=ai_baseline_score
            )
    
    async def _score_tool(self, tool: 'ExternalTool', task: Task) -> float:
        """
        Score tool suitability.
        
        Factors:
        - Task type match
        - Historical success rate
        - Trust score
        - Performance score
        """
        
        # Get historical performance
        history = await self.registry.get_tool_history(tool.name, task.description)
        
        score = (
            0.4 * tool.trust_score +
            0.3 * history.success_rate +
            0.3 * history.performance_score
        )
        
        return score
```

**Example Decision Flow:**

```
Task: "Generate system design diagram"

ToolRouter checks:
1. Find tools: [eraser-cli, mermaid-cli]
2. Score eraser-cli: 0.92 (high trust, proven for diagrams)
3. Score mermaid-cli: 0.78
4. AI baseline: 0.70
5. Decision: Use eraser-cli (31% better than AI)

Manager executes:
- Install eraser-cli if needed
- Run in sandbox
- Validate output
- Integrate diagram
```

---

### 4. Tool Registry & Sandbox

**File**: `archon/tools/tool_registry.py`

```json
{
  "tools": [
    {
      "name": "eraser-cli",
      "description": "Generate system design diagrams",
      "task_types_supported": [
        "system_design_diagram",
        "architecture_diagram",
        "sequence_diagram"
      ],
      "installation_method": "npm install -g eraser-cli",
      "sandbox_required": true,
      "trust_score": 0.95,
      "performance_score": 0.92,
      "avg_execution_time_ms": 1500,
      "success_rate": 0.98,
      "output_format": "svg",
      "validation_schema": {
        "type": "file",
        "extension": ".svg",
        "min_size_bytes": 1000
      }
    },
    {
      "name": "terraform",
      "description": "Infrastructure as code",
      "task_types_supported": [
        "infrastructure_provisioning",
        "cloud_deployment"
      ],
      "installation_method": "brew install terraform",
      "sandbox_required": true,
      "trust_score": 0.98,
      "performance_score": 0.95,
      "requires_credentials": true
    }
  ]
}
```

**File**: `archon/tools/tool_sandbox.py`

```python
import subprocess
import tempfile
import os
from pathlib import Path

class ToolSandbox:
    """
    Executes external tools in isolated environment.
    
    Security requirements:
    - Limited filesystem access
    - No network by default
    - Resource limits (CPU, memory, time)
    - All execution logged
    """
    
    async def execute(self, tool: ExternalTool, input_data: Dict) -> ToolResult:
        """
        Execute tool in sandbox.
        
        Steps:
        1. Create isolated temp directory
        2. Prepare input files
        3. Execute with resource limits
        4. Validate output
        5. Clean up
        6. Log execution
        """
        
        with tempfile.TemporaryDirectory() as sandbox_dir:
            # Prepare input
            input_file = Path(sandbox_dir) / "input.json"
            input_file.write_text(json.dumps(input_data))
            
            # Build command
            cmd = self._build_command(tool, input_file, sandbox_dir)
            
            # Execute with limits
            try:
                result = subprocess.run(
                    cmd,
                    cwd=sandbox_dir,
                    capture_output=True,
                    timeout=300,  # 5 min max
                    env=self._get_restricted_env()
                )
                
                # Validate output
                output = self._validate_output(
                    result, 
                    tool.validation_schema, 
                    sandbox_dir
                )
                
                # Log execution
                await self._log_execution(tool, input_data, output, result)
                
                return ToolResult(
                    success=result.returncode == 0,
                    output=output,
                    execution_time_ms=result.elapsed_time,
                    logs=result.stderr.decode()
                )
                
            except subprocess.TimeoutExpired:
                return ToolResult(
                    success=False,
                    error="Tool execution timeout",
                    execution_time_ms=300_000
                )
    
    def _get_restricted_env(self) -> Dict[str, str]:
        """
        Restricted environment variables.
        
        Only allow:
        - PATH (limited)
        - HOME (sandbox)
        - No AWS/GCP credentials
        """
        return {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp/archon_sandbox"
        }
```

---

### 5. Arbitrator (Deliberation Protocol)

**File**: `archon/deliberation/protocol.py`

```python
from typing import List
from dataclasses import dataclass

@dataclass
class AgentProposal:
    agent: str
    proposal: str
    reasoning: str
    risk_score: float
    complexity_score: float
    estimated_time_hours: float

@dataclass
class Conflict:
    conflict_id: str
    conflict_type: str
    agents_involved: List[str]
    proposals: List[AgentProposal]

class Arbitrator:
    """
    Resolves conflicts between agents using structured deliberation.
    
    Protocol:
    1. Agents submit structured proposals (JSON)
    2. Manager evaluates each proposal
    3. Manager chooses final approach
    4. Decision is logged with reasoning
    """
    
    async def resolve_conflict(self, task: Task, conflict: Conflict) -> Decision:
        """
        Structured conflict resolution.
        
        Evaluation criteria:
        - Risk score (lower better)
        - Complexity score (lower better for MVP)
        - Time estimate
        - Alignment with project goals
        """
        
        scores = {}
        
        for proposal in conflict.proposals:
            score = self._evaluate_proposal(proposal, task.context)
            scores[proposal.agent] = score
        
        # Select best proposal
        best_agent = max(scores, key=scores.get)
        chosen_proposal = next(p for p in conflict.proposals if p.agent == best_agent)
        
        # Create decision
        decision = Decision(
            conflict_id=conflict.conflict_id,
            chosen_agent=best_agent,
            chosen_proposal=chosen_proposal.proposal,
            reasoning=self._generate_reasoning(chosen_proposal, scores),
            timestamp=datetime.now()
        )
        
        # Log decision
        await self._log_decision(decision)
        
        return decision
    
    def _evaluate_proposal(self, proposal: AgentProposal, context: Dict) -> float:
        """
        Multi-criteria evaluation.
        
        Weights:
        - Risk: 40%
        - Complexity: 30%
        - Time: 20%
        - Goal alignment: 10%
        """
        
        project_phase = context.get("project_phase", "mvp")
        
        # Lower risk is better
        risk_score = 1.0 - proposal.risk_score
        
        # Lower complexity is better for MVP
        complexity_weight = 0.5 if project_phase == "mvp" else 0.8
        complexity_score = 1.0 - (proposal.complexity_score * complexity_weight)
        
        # Faster is better
        time_score = 1.0 / (1.0 + proposal.estimated_time_hours / 10.0)
        
        total_score = (
            0.4 * risk_score +
            0.3 * complexity_score +
            0.2 * time_score +
            0.1  # goal alignment placeholder
        )
        
        return total_score
```

**Example Deliberation:**

```json
{
  "conflict_id": "arch_001",
  "conflict_type": "architectural_decision",
  "agents_involved": ["backend", "frontend", "devops"],
  "proposals": [
    {
      "agent": "backend",
      "proposal": "microservices_architecture",
      "reasoning": "Scalability, team autonomy, independent deployment",
      "risk_score": 0.6,
      "complexity_score": 0.8,
      "estimated_time_hours": 120
    },
    {
      "agent": "frontend",
      "proposal": "monolith_with_modular_frontend",
      "reasoning": "Faster iteration, simpler deployment, lower ops overhead",
      "risk_score": 0.3,
      "complexity_score": 0.4,
      "estimated_time_hours": 40
    }
  ],
  "manager_decision": {
    "chosen_proposal": "monolith_with_modular_frontend",
    "reasoning": "Project phase=MVP, team size=2, speed>scale. Microservices add unnecessary complexity. Can refactor later if needed.",
    "override_conditions": "Revisit if: users > 10k OR team > 5 OR deployment frequency > 10/day"
  }
}
```

---

## Next: Scaffolding Code

See next response for:
- CLI implementation
- Agent base classes
- Database schemas
- Example execution trace
