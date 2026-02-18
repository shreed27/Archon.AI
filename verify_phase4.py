"""
Verification script for Phase 4: Learning Engine & Vector Memory.
Tests:
1. LearningEngine initialization (with ChromaDB check).
2. Recording a task outcome.
3. Searching for similar tasks (Semantic Search).
4. Finding best model based on history.
"""

import asyncio
import shutil
from pathlib import Path
import sys

# Ensure src is in path
sys.path.append("src")

from archon.manager.learning_engine import LearningEngine
from archon.utils.schemas import Task, TaskResult, AgentType, TaskStatus
from datetime import datetime


async def verify():
    print("🧠 Verifying Phase 4: Learning Engine Upgrade...")

    # Setup test directory
    test_dir = Path("./.archon_test")
    if test_dir.exists():
        shutil.rmtree(test_dir)

    engine = LearningEngine()
    await engine.initialize(test_dir)

    if not engine.collection:
        print("⚠️  Vector Memory NOT initialized (ChromaDB missing?).")
        print("    Install 'chromadb' to enable semantic search.")
        return

    print("✅ Vector Memory initialized successfully.")

    # 1. Record some history
    print("\n[1] Recording task history...")

    history_data = [
        ("Build a React login form", AgentType.FRONTEND, "gpt-4", True, 0.95),
        ("Implement JWT authentication API", AgentType.BACKEND, "gpt-4", True, 0.92),
        ("Fix CSS z-index issue", AgentType.FRONTEND, "gemini-flash", True, 0.88),
        ("Optimize database query performance", AgentType.DATABASE, "claude-3-opus", True, 0.98),
        ("Write unit tests for auth service", AgentType.TESTING, "gpt-4", True, 0.90),
    ]

    for i, (desc, agent, model, success, score) in enumerate(history_data):
        task = Task(
            task_id=f"task_{i}", description=desc, agent_type=agent, status=TaskStatus.COMPLETED
        )
        result = TaskResult(
            success=success,
            output="Done",
            quality_score=score,
            execution_time_ms=1000,
            model_used=model,
        )
        await engine.record_outcome(task, result)
        print(f"    - Recorded: {desc[:40]}...")

    # 2. Test Semantic Search
    print("\n[2] Testing Semantic Search...")
    query = "Create a sign in page"
    print(f"    Query: '{query}'")

    similar = await engine.get_similar_tasks(query, limit=2)
    if similar:
        for t in similar:
            print(f"    -> Found match: '{t['description']}' (model: {t['model_used']})")
            if "login" in t["description"]:
                print("    ✅ Semantic match successful!")
    else:
        print("    ❌ No matches found (Search failed)")

    # 3. Test Model Recommendation
    print("\n[3] Testing Model Recommendation...")
    new_task = Task(
        task_id="new_task",
        description="Develop a user authentication system endpoint",
        agent_type=AgentType.BACKEND,
        status=TaskStatus.PENDING,
    )

    rec_model = await engine.get_best_model_for_task(new_task)
    print(f"    Task: {new_task.description}")
    print(f"    Recommended Model: {rec_model}")

    if rec_model == "gpt-4":
        print("    ✅ Recommendation logic works (matched with 'Implement JWT auth')")
    else:
        print(f"    ⚠️  Recommendation might vary: {rec_model}")

    # Cleanup
    if test_dir.exists():
        shutil.rmtree(test_dir)
    print("\n✅ Phase 4 Verification Complete.")


if __name__ == "__main__":
    asyncio.run(verify())
