# Example Execution Trace: SaaS with JWT Auth

This document shows a complete execution trace of ARCHON building a SaaS application with JWT authentication.

## User Input

```bash
archon start
```

**Manager:** What are we building?

**User:** Build a SaaS application with JWT authentication and generate a system design diagram.

---

## Manager Analysis

```
[2026-02-15 15:45:00] Manager analyzing goal...
[2026-02-15 15:45:02] Goal parsed into specification
```

**Manager Decision Log:**

```json
{
  "goal": "Build SaaS application with JWT authentication",
  "components": ["backend", "frontend", "authentication", "database"],
  "architecture": {
    "type": "monolith",
    "reason": "MVP phase, small team, speed > scale"
  },
  "tasks": [
    {
      "id": "task_001",
      "description": "Generate system design diagram",
      "agent": "documentation",
      "tool_vs_ai_decision": "pending"
    },
    {
      "id": "task_002",
      "description": "Design database schema for users and sessions",
      "agent": "backend",
      "dependencies": []
    },
    {
      "id": "task_003",
      "description": "Implement JWT authentication endpoints",
      "agent": "backend",
      "dependencies": ["task_002"]
    },
    {
      "id": "task_004",
      "description": "Build login/signup UI components",
      "agent": "frontend",
      "dependencies": ["task_003"]
    }
  ]
}
```

---

## Task 001: System Design Diagram

### Tool vs AI Decision

```
[2026-02-15 15:45:03] ToolRouter evaluating task_001
[2026-02-15 15:45:03] Task type inferred: system_design_diagram
[2026-02-15 15:45:03] Found candidate tools: [eraser-cli]
[2026-02-15 15:45:03] Tool score: 0.92
[2026-02-15 15:45:03] AI baseline: 0.70
[2026-02-15 15:45:03] Decision: USE TOOL (eraser-cli outperforms AI by 31%)
```

**Manager:** Using external tool: eraser-cli

### Tool Execution

```
[2026-02-15 15:45:04] ToolSandbox: Installing eraser-cli
[2026-02-15 15:45:06] ToolSandbox: Creating isolated environment
[2026-02-15 15:45:06] ToolSandbox: Executing eraser-cli
[2026-02-15 15:45:08] ToolSandbox: Validating output
[2026-02-15 15:45:08] ToolSandbox: Output valid (SVG, 45KB)
```

**Output:** `docs/system_design.svg`

```
✓ Documentation agent completed: Generate system design diagram
  Tool used: eraser-cli
  Execution time: 4.2s
  Quality score: 0.95
```

---

## Task 002: Database Schema

### Model Selection

```
[2026-02-15 15:45:09] ModelRouter evaluating task_002
[2026-02-15 15:45:09] Task complexity: 0.6
[2026-02-15 15:45:09] Reasoning depth: 0.7
[2026-02-15 15:45:09] Context size: 8,000 tokens
[2026-02-15 15:45:09] Model scores:
  - GPT-4 Turbo: 0.87
  - Claude Opus: 0.82
  - Gemini Flash: 0.71
[2026-02-15 15:45:09] Selected: GPT-4 Turbo (best reasoning for DB design)
```

### Agent Execution

```
→ Backend agent starting: Design database schema for users and sessions
[2026-02-15 15:45:10] BackendAgent executing with GPT-4 Turbo
[2026-02-15 15:45:15] BackendAgent received response
[2026-02-15 15:45:15] BackendAgent validating output
```

**Output:**

```sql
-- migrations/001_create_users.sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- migrations/002_create_sessions.sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token_hash ON sessions(token_hash);
```

```
✓ Backend agent completed: Design database schema
  Model used: GPT-4 Turbo
  Files created: 2
  Execution time: 5.3s
  Quality score: 0.92
```

---

## Task 003: JWT Authentication

### Model Selection

```
[2026-02-15 15:45:16] ModelRouter evaluating task_003
[2026-02-15 15:45:16] Task complexity: 0.8 (security-critical)
[2026-02-15 15:45:16] Reasoning depth: 0.9
[2026-02-15 15:45:16] Selected: GPT-4 Turbo (high reasoning for auth logic)
```

### Agent Execution

```
→ Backend agent starting: Implement JWT authentication endpoints
[2026-02-15 15:45:17] BackendAgent executing with GPT-4 Turbo
[2026-02-15 15:45:25] BackendAgent received response
[2026-02-15 15:45:25] QualityGate: Running security checks
[2026-02-15 15:45:26] QualityGate: PASSED (score: 0.88)
```

**Output Files:**

- `src/auth/jwt_handler.py`
- `src/auth/password_hasher.py`
- `src/api/auth_endpoints.py`
- `tests/test_auth.py`

```
✓ Backend agent completed: Implement JWT authentication
  Model used: GPT-4 Turbo
  Files created: 4
  Execution time: 9.2s
  Quality score: 0.88
```

---

## Task 004: Login/Signup UI

### Model Selection

```
[2026-02-15 15:45:27] ModelRouter evaluating task_004
[2026-02-15 15:45:27] Task complexity: 0.5 (UI component)
[2026-02-15 15:45:27] Speed priority: 0.8
[2026-02-15 15:45:27] Selected: Gemini Flash (fast iteration for UI)
```

### Agent Execution

```
→ Frontend agent starting: Build login/signup UI components
[2026-02-15 15:45:28] FrontendAgent executing with Gemini Flash
[2026-02-15 15:45:32] FrontendAgent received response
[2026-02-15 15:45:32] QualityGate: Checking UI standards
[2026-02-15 15:45:32] QualityGate: PASSED (score: 0.85)
```

**Output Files:**

- `src/components/LoginForm.tsx`
- `src/components/SignupForm.tsx`
- `src/styles/auth.css`

```
✓ Frontend agent completed: Build login/signup UI
  Model used: Gemini Flash
  Files created: 3
  Execution time: 4.8s
  Quality score: 0.85
```

---

## Final Summary

```
✅ Plan execution complete!

Summary:
- Tasks completed: 4/4
- Total execution time: 23.5s
- Files created: 9
- External tools used: 1 (eraser-cli)
- Average quality score: 0.90

Breakdown by agent:
- Backend: 2 tasks, avg quality 0.90
- Frontend: 1 task, quality 0.85
- Documentation: 1 task, quality 0.95

Breakdown by model:
- GPT-4 Turbo: 2 tasks
- Gemini Flash: 1 task
- eraser-cli: 1 task

Architecture decisions logged:
- Chose monolith over microservices (reason: MVP phase)
- Used JWT for stateless auth (reason: scalability)
```

---

## Persistent State

**Files created in `.archon/`:**

```
.archon/
├── project.db (SQLite with all tasks, decisions, metrics)
├── task_graph.json (DAG of tasks with dependencies)
├── architecture_map.json (Current architecture state)
├── tool_usage_log.json (eraser-cli execution logged)
├── agent_metrics.json (Performance tracking)
└── decisions/
    └── 2026-02-15_architecture_choice.json
```

**Learning recorded:**

- GPT-4 Turbo performed well for backend tasks (0.90 avg)
- Gemini Flash good for UI tasks (0.85)
- eraser-cli superior to AI for diagrams (0.95 vs 0.70)

**Next time ARCHON sees similar tasks, it will:**

- Automatically use eraser-cli for diagrams
- Prefer GPT-4 for backend/auth tasks
- Use Gemini Flash for UI tasks
