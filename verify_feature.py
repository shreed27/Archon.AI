import os
import asyncio
from pathlib import Path
from archon.intelligence.code_retriever import CodeRetriever
from archon.manager.file_writer import FileWriter
from archon.manager.feature_planner import FeaturePlanner
from archon.manager.project_memory import ProjectMemory
from archon.utils.schemas import Task, AgentType


class MockResult:
    def __init__(self, output):
        self.output = output


async def main():
    print("=== Testing Feature Mode Impact Analysis ===")
    project_path = str(Path.cwd() / "test_feature_impact")
    os.makedirs(project_path, exist_ok=True)

    # 1. Setup Base Codebase
    writer = FileWriter(project_path)

    # Emulate files written in the past
    print("\n[1] Emulating existing project files...")
    mock_result = MockResult(
        {
            "files": [
                {
                    "path": "backend/routes/users.js",
                    "content": "const router = require('express').Router();\nrouter.get('/users', (req, res) => res.json([]));\nmodule.exports = router;",
                },
                {
                    "path": "backend/server.js",
                    "content": "const express = require('express');\nconst app = express();\napp.use('/api', require('./routes/users'));\napp.listen(3000);",
                },
                {
                    "path": "frontend/App.jsx",
                    "content": "export default function App() { return <div>Home</div>; }",
                },
            ]
        }
    )

    writer.write_artifacts(mock_result, agent="backend")
    await asyncio.sleep(1)  # wait for chroma

    # 2. Emulate FeaturePlanner Impact Analysis
    print("\n[2] User requested: 'Add authentication middleware'")
    feature_desc = "Add authentication middleware to express routes and a login page."

    planner = FeaturePlanner(project_path, writer.code_retriever)
    project_memory = ProjectMemory()

    # This invokes CodeRetriever search inherently
    spec = await planner.generate_feature_plan(
        feature_description=feature_desc,
        codebase_index=project_memory.codebase_index,
        project_memory=project_memory,
    )

    print("\n[3] Impact Analysis Results & Task Generation:")

    print(f"Goal: {spec['goal']}")
    if "tasks" in spec and len(spec["tasks"]) > 0:
        for idx, t in enumerate(spec["tasks"]):
            print(f"Task {idx + 1}: [{t.get('agent', 'unknown')}] {t.get('description', '')}")
    else:
        print("Mock fallback tasks received (No API key to compute real tasks)")

    print("\nImpacted files context (what the planner read):")
    # Doing the same search to show what it found
    relevant = writer.code_retriever.search(feature_desc, top_k=3)
    for r in relevant:
        print(f"  -> {r['path']}")


if __name__ == "__main__":
    asyncio.run(main())
