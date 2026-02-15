# ARCHON Folder Structure

```
archon/
├── README.md
├── pyproject.toml
├── setup.py
│
├── archon/
│   ├── __init__.py
│   ├── __main__.py                    # CLI entry point
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── commands.py                # start, resume, status
│   │   └── conversation.py            # Conversational interface
│   │
│   ├── manager/
│   │   ├── __init__.py
│   │   ├── orchestrator.py            # Main Manager class
│   │   ├── model_router.py            # Model selection engine
│   │   ├── tool_router.py             # Tool vs AI decision engine
│   │   ├── task_scheduler.py          # DAG construction & scheduling
│   │   ├── arbitrator.py              # Conflict resolution
│   │   ├── quality_gate.py            # Quality enforcement
│   │   └── learning_engine.py         # Cross-project learning
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py              # Abstract base class
│   │   ├── backend_agent.py
│   │   ├── frontend_agent.py
│   │   ├── devops_agent.py
│   │   ├── security_agent.py
│   │   ├── testing_agent.py
│   │   ├── integration_agent.py
│   │   ├── documentation_agent.py
│   │   └── git_agent.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── model_interface.py         # Abstract model interface
│   │   ├── openai_client.py           # GPT-4 integration
│   │   ├── anthropic_client.py        # Claude integration
│   │   ├── google_client.py           # Gemini integration
│   │   └── model_selector.py          # Selection logic
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── tool_registry.py           # Tool catalog management
│   │   ├── tool_installer.py          # Auto-install tools
│   │   ├── tool_sandbox.py            # Isolated execution
│   │   ├── tool_validator.py          # Output validation
│   │   └── builtin_tools/
│   │       ├── eraser_cli.py
│   │       ├── terraform.py
│   │       ├── playwright.py
│   │       └── semgrep.py
│   │
│   ├── intelligence/
│   │   ├── __init__.py
│   │   ├── ast_parser.py              # Tree-sitter integration
│   │   ├── dependency_analyzer.py     # Dependency graph
│   │   ├── coupling_detector.py       # Coupling metrics
│   │   ├── drift_detector.py          # Architecture drift
│   │   └── static_analyzer.py         # Static analysis
│   │
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── database.py                # SQLite operations
│   │   ├── file_tracker.py            # File ownership
│   │   ├── task_graph.py              # DAG persistence
│   │   ├── architecture_state.py      # Architecture tracking
│   │   ├── risk_registry.py           # Risk tracking
│   │   └── vector_store.py            # Embeddings for RAG
│   │
│   ├── deliberation/
│   │   ├── __init__.py
│   │   ├── protocol.py                # Deliberation protocol
│   │   ├── proposal_schema.py         # JSON schemas
│   │   └── decision_logger.py         # Audit logging
│   │
│   ├── simulation/
│   │   ├── __init__.py
│   │   ├── scale_simulator.py         # Scale testing
│   │   ├── chaos_engine.py            # Chaos engineering
│   │   └── bottleneck_detector.py     # Performance analysis
│   │
│   ├── security/
│   │   ├── __init__.py
│   │   ├── sandbox.py                 # Sandbox implementation
│   │   ├── permissions.py             # Permission management
│   │   └── audit_log.py               # Security logging
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── config.py
│       └── schemas.py                 # Pydantic models
│
├── tests/
│   ├── unit/
│   │   ├── test_manager/
│   │   ├── test_agents/
│   │   ├── test_models/
│   │   └── test_tools/
│   │
│   ├── integration/
│   │   ├── test_end_to_end.py
│   │   ├── test_deliberation.py
│   │   └── test_tool_execution.py
│   │
│   └── fixtures/
│       ├── sample_projects/
│       └── mock_responses/
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── FOLDER_STRUCTURE.md
│   ├── IMPLEMENTATION.md
│   ├── API_REFERENCE.md
│   └── EXAMPLES.md
│
├── examples/
│   ├── saas_with_auth/
│   │   ├── conversation.log
│   │   └── .archon/
│   │
│   └── system_design_diagram/
│       ├── conversation.log
│       └── .archon/
│
└── scripts/
    ├── install.sh
    ├── setup_dev.sh
    └── run_tests.sh
```

## Project-Specific Structure

When ARCHON manages a project, it creates:

```
your-project/
├── .archon/
│   ├── project.db
│   ├── task_graph.json
│   ├── file_map.json
│   ├── architecture_map.json
│   ├── risk_map.json
│   ├── agent_metrics.json
│   ├── tool_registry.json
│   ├── tool_usage_log.json
│   ├── project_dna.json
│   ├── memory.vec
│   │
│   ├── agent_logs/
│   │   ├── backend/
│   │   │   ├── 2026-02-15_task_001.log
│   │   │   └── 2026-02-15_task_002.log
│   │   ├── frontend/
│   │   ├── devops/
│   │   └── manager/
│   │
│   ├── decisions/
│   │   ├── 2026-02-15_architecture_choice.json
│   │   └── 2026-02-15_tool_selection.json
│   │
│   └── sandbox/
│       ├── eraser-cli/
│       └── terraform/
│
├── src/
├── tests/
└── docs/
```

## Key Files Explained

### Manager Core
- **orchestrator.py**: Main Manager class, coordinates all subsystems
- **model_router.py**: Selects optimal AI model per task
- **tool_router.py**: Decides when to use external tools vs AI
- **arbitrator.py**: Resolves conflicts between agents

### Agents
- **base_agent.py**: Abstract class defining agent interface
- **[domain]_agent.py**: Specialized agents for each domain

### Tools
- **tool_registry.py**: Manages catalog of external tools
- **tool_sandbox.py**: Executes tools in isolated environment
- **tool_validator.py**: Validates tool outputs against schemas

### Intelligence
- **ast_parser.py**: Parses code into AST using Tree-sitter
- **drift_detector.py**: Detects when code diverges from architecture
- **coupling_detector.py**: Measures coupling between modules

### Persistence
- **database.py**: SQLite operations for tasks, files, decisions
- **task_graph.py**: DAG persistence and querying
- **vector_store.py**: Embeddings for semantic search

## Configuration Files

### pyproject.toml
```toml
[tool.poetry]
name = "archon-ai"
version = "0.1.0"
description = "Autonomous Engineering Organization CLI"

[tool.poetry.dependencies]
python = "^3.11"
click = "^8.1.0"
pydantic = "^2.0.0"
sqlalchemy = "^2.0.0"
openai = "^1.0.0"
anthropic = "^0.18.0"
google-generativeai = "^0.3.0"
tree-sitter = "^0.20.0"
networkx = "^3.0"
chromadb = "^0.4.0"

[tool.poetry.scripts]
archon = "archon.__main__:main"
```

### .archon/project.db Schema
```sql
-- See ARCHITECTURE.md for full schema
```

### .archon/tool_registry.json
```json
{
  "tools": [
    {
      "name": "eraser-cli",
      "task_types": ["system_design_diagram"],
      "installation": "npm install -g eraser-cli",
      "trust_score": 0.95
    }
  ]
}
```

## Development Workflow

1. **Local Development**:
   ```bash
   cd archon/
   poetry install
   poetry run archon start
   ```

2. **Testing**:
   ```bash
   poetry run pytest tests/
   ```

3. **Building**:
   ```bash
   poetry build
   ```

4. **Installation**:
   ```bash
   pip install archon-ai
   ```
