# ARCHON.AI

**Autonomous Engineering Organization CLI**

A production-grade, distributed, multi-agent AI engineering operating system.

## What is ARCHON?

ARCHON is not a chatbot. It's not a single-model wrapper. It's not a single-agent system.

ARCHON is a **persistent, deliberative, model-aware, tool-aware AI-native engineering organization**.

Think of it as:
- **Kubernetes** for AI agents
- **Terraform** for software architecture
- **GitHub Actions** meets **AI orchestration**

## Core Capabilities

- 🧠 **Intelligent Model Routing**: Dynamically assigns optimal AI model per task (GPT-4, Claude, Gemini)
- 🔧 **Tool Orchestration**: Detects when external CLI tools outperform AI models
- 🏗️ **Architecture Intelligence**: Maintains project knowledge graph, detects drift
- 👥 **Multi-Agent Deliberation**: Structured conflict resolution with Manager arbitration
- 📊 **Cross-Project Learning**: Improves routing decisions over time
- 🔒 **Production Security**: Sandboxed tool execution, file-level ownership
- 🎯 **Quality Gates**: AST analysis, coupling detection, static analysis

## Quick Start

```bash
# 1. Download System
./bin/archon download

# 2. Initialize Neural Engine
./bin/archon start
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MANAGER                              │
│  (Orchestrator, Router, Arbitrator, Validator)              │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
   │ AI      │         │ AI      │        │ External│
   │ Models  │         │ Agents  │        │ Tools   │
   └─────────┘         └─────────┘        └─────────┘
   GPT-4                Backend            Eraser CLI
   Claude               Frontend           Terraform
   Gemini               DevOps             Playwright
                        Security
                        Testing
```

## System Design

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed system design.

## License

MIT
