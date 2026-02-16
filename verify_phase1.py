#!/usr/bin/env python3
"""
Verification script for Phase 1 components.
Tests that all modules can be imported successfully.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all Phase 1 components can be imported."""

    print("🔍 Testing Phase 1 Component Imports...\n")

    tests = []

    # Manager Components
    print("📋 Manager Components:")
    try:
        from archon.manager.task_scheduler import TaskScheduler

        print("  ✅ TaskScheduler")
        tests.append(("TaskScheduler", True))
    except Exception as e:
        print(f"  ❌ TaskScheduler: {e}")
        tests.append(("TaskScheduler", False))

    try:
        from archon.manager.arbitrator import Arbitrator

        print("  ✅ Arbitrator")
        tests.append(("Arbitrator", True))
    except Exception as e:
        print(f"  ❌ Arbitrator: {e}")
        tests.append(("Arbitrator", False))

    try:
        from archon.manager.quality_gate import QualityGate

        print("  ✅ QualityGate")
        tests.append(("QualityGate", True))
    except Exception as e:
        print(f"  ❌ QualityGate: {e}")
        tests.append(("QualityGate", False))

    try:
        from archon.manager.learning_engine import LearningEngine

        print("  ✅ LearningEngine")
        tests.append(("LearningEngine", True))
    except Exception as e:
        print(f"  ❌ LearningEngine: {e}")
        tests.append(("LearningEngine", False))

    # Persistence Layer
    print("\n💾 Persistence Layer:")
    try:
        from archon.persistence.database import Database

        print("  ✅ Database")
        tests.append(("Database", True))
    except Exception as e:
        print(f"  ❌ Database: {e}")
        tests.append(("Database", False))

    try:
        from archon.persistence.task_graph import TaskGraph

        print("  ✅ TaskGraph")
        tests.append(("TaskGraph", True))
    except Exception as e:
        print(f"  ❌ TaskGraph: {e}")
        tests.append(("TaskGraph", False))

    try:
        from archon.persistence.architecture_state import ArchitectureState

        print("  ✅ ArchitectureState")
        tests.append(("ArchitectureState", True))
    except Exception as e:
        print(f"  ❌ ArchitectureState: {e}")
        tests.append(("ArchitectureState", False))

    # Model Clients
    print("\n🤖 Model Clients:")
    try:
        from archon.models.openai_client import OpenAIClient

        print("  ✅ OpenAIClient")
        tests.append(("OpenAIClient", True))
    except Exception as e:
        print(f"  ❌ OpenAIClient: {e}")
        tests.append(("OpenAIClient", False))

    try:
        from archon.models.anthropic_client import AnthropicClient

        print("  ✅ AnthropicClient")
        tests.append(("AnthropicClient", True))
    except Exception as e:
        print(f"  ❌ AnthropicClient: {e}")
        tests.append(("AnthropicClient", False))

    try:
        from archon.models.google_client import GoogleClient

        print("  ✅ GoogleClient")
        tests.append(("GoogleClient", True))
    except Exception as e:
        print(f"  ❌ GoogleClient: {e}")
        tests.append(("GoogleClient", False))

    # Tool System
    print("\n🛠️  Tool System:")
    try:
        from archon.tools.tool_sandbox import ToolSandbox

        print("  ✅ ToolSandbox")
        tests.append(("ToolSandbox", True))
    except Exception as e:
        print(f"  ❌ ToolSandbox: {e}")
        tests.append(("ToolSandbox", False))

    try:
        from archon.tools.tool_registry import ToolRegistry

        print("  ✅ ToolRegistry")
        tests.append(("ToolRegistry", True))
    except Exception as e:
        print(f"  ❌ ToolRegistry: {e}")
        tests.append(("ToolRegistry", False))

    # Summary
    print("\n" + "=" * 50)
    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    print(f"\n📊 Results: {passed}/{total} components imported successfully")

    if passed == total:
        print("✅ All Phase 1 components are working!")
        return 0
    else:
        print(f"❌ {total - passed} component(s) failed to import")
        return 1


if __name__ == "__main__":
    sys.exit(test_imports())
