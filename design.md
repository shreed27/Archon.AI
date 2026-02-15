# ARCHON.AI System Design

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MANAGER LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Orchestrator │  │ Model Router │  │ Tool Router  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Arbitrator  │  │ Quality Gate │  │   Learning   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼──────┐
│   AI MODELS    │  │     AGENTS     │  │    TOOLS    │
├────────────────┤  ├────────────────┤  ├─────────────┤
│ • GPT-4        │  │ • Backend      │  │ • Eraser    │
│ • Claude Opus  │  │ • Frontend     │  │ • Terraform │
│ • Gemini Flash │  │ • DevOps       │  │ • Playwright│
│                │  │ • Security     │  │ • Semgrep   │
│                │  │ • Testing      │  │             │
└────────────────┘  └────────────────┘  └─────────────┘
                            │
                    ┌───────▼────────┐
                    │  PERSISTENCE   │
                    ├────────────────┤
                    │ • SQLite DB    │
                    │ • Task Graph   │
                    │ • Arch Map     │
                    │ • Vector Store │
                    └────────────────┘
```

### 1.2 Component Responsibilities

| Component | Responsibility | Never Does |
|-----------|---------------|------------|
| Manager | Orchestrate, route, arbitrate | Write code directly |
| Model Router | Select optimal AI model | Execute tasks |
| Tool Router | Decide tool vs AI | Install tools without confirmation |
| Agents | Execute tasks, write code | Make architectural decisions alone |
| Quality Gate | Validate outputs | Modify code |
| Learning Engine | Improve routing over time | Store PII |

## 2. Data Architecture

### 2.1 Database Schema

```sql
-- Tasks table
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    parent_task_id TEXT,
    description TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    model_assigned TEXT,
    tool_assigned TEXT,
    status TEXT NOT NULL,
    quality_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    context JSON,
    FOREIGN KEY (parent_task_id) REFERENCES tasks(task_id)
);

-- Files table
CREATE TABLE files (
    file_path TEXT PRIMARY KEY,
    owner_agent TEXT NOT NULL,
    last_modified_by TEXT NOT NULL,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lines_of_code INTEGER,
    complexity_score REAL,
    coupling_score REAL,
    last_quality_score REAL
);

-- Decisions table
CREATE TABLE decisions (
    decision_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL,
    agents_involved TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    override_conditions TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context JSON
);

-- Model performance table
CREATE TABLE model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    model_name TEXT NOT NULL,
    quality_score REAL NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tool usage table
CREATE TABLE tool_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    task_id TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    execution_time_ms INTEGER NOT NULL,
    input_hash TEXT,
    output_hash TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

-- Indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_agent ON tasks(agent_type);
CREATE INDEX idx_files_owner ON files(owner_agent);
CREATE INDEX idx_model_perf_task ON model_performance(task_type, model_name);
CREATE INDEX idx_tool_usage_tool ON tool_usage(tool_name);
```

### 2.2 File System Structure

```
project_root/
├── .archon/
│   ├── project.db                 # SQLite database
│   ├── task_graph.json            # Task DAG
│   ├── file_map.json              # File ownership
│   ├── architecture_map.json      # System architecture state
│   ├── risk_map.json              # Risk registry
│   ├── agent_metrics.json         # Performance tracking
│   ├── tool_registry.json         # External tool catalog
│   ├── tool_usage_log.json        # Tool execution history
│   ├── project_dna.json           # Project fingerprint
│   ├── memory.vec                 # Vector embeddings
│   ├── agent_logs/
│   │   ├── backend/
│   │   ├── frontend/
│   │   ├── devops/
│   │   └── manager/
│   ├── decisions/                 # Deliberation logs
│   └── sandbox/                   # Tool execution sandbox
├── src/
└── ...
```

### 2.3 JSON Schemas

**Task Schema:**
```json
{
  "task_id": "uuid",
  "description": "string",
  "agent_type": "backend|frontend|devops|security|testing|integration|documentation|git",
  "model_assigned": "gpt-4|claude-opus-3|gemini-2.0-flash|null",
  "tool_assigned": "string|null",
  "status": "pending|assigned|in_progress|needs_deliberation|completed|failed",
  "dependencies": ["task_id"],
  "quality_threshold": 0.8,
  "context": {
    "project_phase": "mvp|scale",
    "team_size": 2,
    "constraints": []
  }
}
```

**Agent Proposal Schema:**
```json
{
  "agent": "backend",
  "proposal": "microservices_architecture",
  "reasoning": "Scalability, team autonomy",
  "risk_score": 0.6,
  "complexity_score": 0.8,
  "estimated_time_hours": 120,
  "dependencies": ["docker", "kubernetes"],
  "alternatives_considered": ["monolith", "modular_monolith"]
}
```

**Tool Registry Entry:**
```json
{
  "name": "eraser-cli",
  "description": "Generate system design diagrams",
  "task_types_supported": ["system_design_diagram", "architecture_diagram"],
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
}
```

## 3. Component Design

### 3.1 Manager Orchestrator

**Class Diagram:**
```python
class ManagerOrchestrator:
    - project_path: str
    - model_router: ModelRouter
    - tool_router: ToolRouter
    - task_scheduler: TaskScheduler
    - arbitrator: Arbitrator
    - quality_gate: QualityGate
    - learning_engine: LearningEngine
    - db: Database
    - task_graph: TaskGraph
    - architecture_map: ArchitectureMap
    
    + process_user_goal(goal: str) -> None
    - _parse_goal_to_spec(goal: str) -> Specification
    - _build_knowledge_graph(spec: Specification) -> KnowledgeGraph
    - _execute_task(task: Task) -> None
    - _execute_with_tool(task: Task, tool: ExternalTool) -> TaskResult
    - _execute_with_agent(task: Task, model: str) -> TaskResult
    - _update_project_state(task: Task, result: TaskResult) -> None
```

**State Machine:**
```
[User Goal] → [Parse] → [Build Knowledge Graph] → [Create Task DAG]
                                                          ↓
[Update State] ← [Validate Quality] ← [Execute] ← [Assign Tasks]
       ↓
[Learn & Improve]
```

### 3.2 Model Router

**Decision Algorithm:**
```python
def select_model(task: Task) -> ModelType:
    criteria = extract_criteria(task)
    scores = {}
    
    for model in AVAILABLE_MODELS:
        score = (
            0.4 * reasoning_match(model, criteria) +
            0.2 * context_adequacy(model, criteria) +
            0.2 * speed_match(model, criteria) +
            0.2 * cost_efficiency(model, criteria)
        )
        
        # Apply historical performance
        score *= historical_weight(model, task.agent_type)
        
        scores[model] = score
    
    return max(scores, key=scores.get)
```

**Model Capabilities Matrix:**

| Model | Max Context | Reasoning | Speed | Cost/1K | Best For |
|-------|------------|-----------|-------|---------|----------|
| GPT-4 | 128K | 0.95 | 0.6 | $0.03 | Complex logic, architecture |
| Claude Opus | 200K | 0.93 | 0.5 | $0.015 | Security, large refactors |
| Claude Sonnet | 200K | 0.88 | 0.7 | $0.003 | Balanced tasks |
| Gemini Pro | 1M | 0.87 | 0.8 | $0.002 | Large context analysis |
| Gemini Flash | 1M | 0.85 | 0.95 | $0.001 | Fast iteration, UI |

### 3.3 Tool Router

**Decision Flow:**
```
Task → Find Candidate Tools → Score Each Tool → Compare with AI Baseline
                                                          ↓
                                                   Score > AI * 1.2?
                                                    ↙           ↘
                                                  Yes           No
                                                   ↓             ↓
                                            Use Tool      Use AI Model
```

**Scoring Function:**
```python
def score_tool(tool: ExternalTool, task: Task) -> float:
    history = get_tool_history(tool.name, task.description)
    
    return (
        0.4 * tool.trust_score +
        0.3 * history.success_rate +
        0.3 * history.performance_score
    )
```

### 3.4 Agent System

**Base Agent Interface:**
```python
class BaseAgent(ABC):
    agent_type: str
    primary_model: ModelType
    tool_fallbacks: List[str]
    
    @abstractmethod
    async def execute(self, task: Task, model: ModelType) -> TaskResult:
        pass
    
    @abstractmethod
    async def validate_output(self, output: Any) -> ValidationResult:
        pass
    
    async def request_deliberation(self, conflict: Conflict) -> None:
        pass
```

**Agent Specializations:**

| Agent | Primary Model | Tool Fallbacks | Quality Metrics |
|-------|--------------|----------------|-----------------|
| Backend | GPT-4 | - | API correctness, test coverage |
| Frontend | Gemini Flash | Figma CLI | Component reusability, a11y |
| DevOps | Claude Sonnet | Terraform, Pulumi | Infrastructure validity |
| Security | Claude Opus | Snyk, Semgrep | Vulnerability count |
| Testing | GPT-4 | Playwright | Test coverage, E2E pass rate |

### 3.5 Arbitrator

**Conflict Resolution Algorithm:**
```python
def resolve_conflict(conflict: Conflict) -> Decision:
    scores = {}
    
    for proposal in conflict.proposals:
        score = (
            0.4 * (1.0 - proposal.risk_score) +
            0.3 * (1.0 - proposal.complexity_score * complexity_weight) +
            0.2 * time_score(proposal.estimated_time_hours) +
            0.1 * goal_alignment_score(proposal)
        )
        scores[proposal.agent] = score
    
    best_agent = max(scores, key=scores.get)
    chosen_proposal = find_proposal(conflict, best_agent)
    
    return Decision(
        chosen_agent=best_agent,
        chosen_proposal=chosen_proposal.proposal,
        reasoning=generate_reasoning(chosen_proposal, scores)
    )
```

### 3.6 Quality Gate

**Validation Pipeline:**
```
Code Output → AST Parse → Static Analysis → Coupling Check → Complexity Check
                                                                      ↓
                                                              Score ≥ Threshold?
                                                                ↙           ↘
                                                              Yes           No
                                                               ↓             ↓
                                                            Accept      Remediate
```

**Quality Metrics:**
```python
class QualityMetrics:
    ast_valid: bool
    static_analysis_issues: int
    coupling_score: float        # 0.0 - 1.0 (lower better)
    complexity_score: float      # 0.0 - 1.0 (lower better)
    test_coverage: float         # 0.0 - 1.0
    security_issues: int
    
    def overall_score(self) -> float:
        return (
            0.3 * (1.0 if self.ast_valid else 0.0) +
            0.2 * max(0, 1.0 - self.static_analysis_issues / 10) +
            0.2 * (1.0 - self.coupling_score) +
            0.15 * (1.0 - self.complexity_score) +
            0.1 * self.test_coverage +
            0.05 * (1.0 if self.security_issues == 0 else 0.5)
        )
```

### 3.7 Tool Sandbox

**Security Model:**
```python
class ToolSandbox:
    def execute(tool: ExternalTool, input_data: Dict) -> ToolResult:
        with isolated_environment() as env:
            env.set_limits(
                max_memory="512MB",
                max_cpu="50%",
                timeout="5m",
                network="isolated",
                filesystem="read-only-except-project"
            )
            
            result = env.run(tool.command, input_data)
            
            validate_output(result, tool.validation_schema)
            log_execution(tool, input_data, result)
            
            return result
```

**Resource Limits:**
- Memory: 512MB default
- CPU: 50% of one core
- Timeout: 5 minutes
- Network: Isolated by default
- Filesystem: Read-only except project directory

### 3.8 Learning Engine

**Learning Loop:**
```
Task Execution → Record Outcome → Aggregate Metrics → Update Weights
                                                              ↓
                                                    Apply to Next Task
```

**Metrics Tracked:**
```python
class LearningMetrics:
    task_type: str
    model_performance: Dict[ModelType, PerformanceStats]
    tool_performance: Dict[str, PerformanceStats]
    common_failures: List[FailurePattern]
    recommended_approach: str
    
class PerformanceStats:
    avg_quality_score: float
    avg_execution_time_ms: int
    success_rate: float
    sample_size: int
```

## 4. Interaction Flows

### 4.1 Task Execution Flow

```
User: "Build a SaaS app with authentication"
  ↓
Manager: Parse goal → Specification
  ↓
Manager: Build knowledge graph
  ↓
Manager: Create task DAG
  - Task 1: Design architecture (Documentation Agent)
  - Task 2: Setup project structure (Backend Agent)
  - Task 3: Implement auth API (Backend Agent)
  - Task 4: Create login UI (Frontend Agent)
  - Task 5: Write tests (Testing Agent)
  ↓
Manager: Assign Task 1 to Documentation Agent
  ↓
Tool Router: Should use eraser-cli? → Yes (score 0.92 vs AI 0.70)
  ↓
Tool Sandbox: Execute eraser-cli
  ↓
Quality Gate: Validate diagram → Pass (score 0.95)
  ↓
Manager: Update state, proceed to Task 2
  ↓
Model Router: Select model for Backend Agent → GPT-4
  ↓
Backend Agent: Execute with GPT-4
  ↓
Quality Gate: Validate code → Pass (score 0.88)
  ↓
... continue for remaining tasks
```

### 4.2 Conflict Resolution Flow

```
Backend Agent: Proposes microservices (risk 0.6, complexity 0.8)
  ↓
Frontend Agent: Proposes monolith (risk 0.3, complexity 0.4)
  ↓
Manager: Detect conflict → Initiate deliberation
  ↓
Arbitrator: Evaluate proposals
  - Context: project_phase=MVP, team_size=2
  - Backend score: 0.45
  - Frontend score: 0.72
  ↓
Arbitrator: Choose monolith
  ↓
Manager: Log decision with reasoning
  ↓
Manager: Assign implementation to Backend Agent
```

### 4.3 Tool vs AI Decision Flow

```
Task: "Generate architecture diagram"
  ↓
Tool Router: Find candidate tools
  - eraser-cli (trust 0.95, success 0.98)
  - mermaid-cli (trust 0.85, success 0.90)
  ↓
Tool Router: Score tools
  - eraser-cli: 0.92
  - mermaid-cli: 0.84
  ↓
Tool Router: Compare with AI baseline (0.70)
  - eraser-cli is 31% better
  ↓
Tool Router: Decision → Use eraser-cli
  ↓
Manager: Check if installed → No
  ↓
Manager: Prompt user → Install eraser-cli? [Y/n]
  ↓
User: Y
  ↓
Tool Sandbox: npm install -g eraser-cli
  ↓
Tool Sandbox: Execute eraser-cli
  ↓
Quality Gate: Validate SVG output → Pass
  ↓
Manager: Integrate diagram into project
```

## 5. Deployment Architecture

### 5.1 Local Development

```
User Machine
├── Python 3.10+ (Poetry)
├── SQLite
├── Optional: Docker (enhanced sandboxing)
└── External Tools (npm, terraform, etc.)
```

### 5.2 API Dependencies

```
External APIs
├── OpenAI API (GPT-4)
├── Anthropic API (Claude)
├── Google AI API (Gemini)
└── Optional: Tool-specific APIs
```

### 5.3 Future: Distributed Architecture

```
┌─────────────┐
│   Manager   │ (Coordinator)
└──────┬──────┘
       │
   ┌───┴───┬───────┬───────┐
   │       │       │       │
┌──▼──┐ ┌──▼──┐ ┌──▼──┐ ┌──▼──┐
│Agent│ │Agent│ │Agent│ │Agent│ (Workers)
└─────┘ └─────┘ └─────┘ └─────┘
```

## 6. Security Considerations

### 6.1 Threat Model

| Threat | Mitigation |
|--------|-----------|
| Malicious tool execution | Sandboxing, trust scores |
| API key exposure | Environment variables, never logged |
| Code injection | AST validation, static analysis |
| Resource exhaustion | CPU/memory/time limits |
| Data exfiltration | Network isolation in sandbox |

### 6.2 Security Controls

- All external tools run in isolated sandbox
- API keys stored in environment variables only
- All tool execution logged with hashes
- User confirmation required for installations
- Static analysis before code execution
- File ownership tracking prevents conflicts

## 7. Monitoring & Observability

### 7.1 Metrics

- Task completion rate
- Model selection accuracy
- Tool execution success rate
- Quality gate pass rate
- Average task execution time
- Cost per task

### 7.2 Logging

- All decisions logged with reasoning
- All tool executions logged with I/O hashes
- All conflicts logged with proposals
- All quality gate results logged
- Agent performance logged per task

## 8. Future Enhancements

- Distributed multi-machine execution
- Web UI dashboard
- Real-time collaboration
- Custom model fine-tuning
- Integration with CI/CD pipelines
- Plugin marketplace for agents/tools
