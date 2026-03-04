import asyncio
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Set a fake key, so the app thinks it has an API key
os.environ["OPENAI_API_KEY"] = "fake-key"

from archon.manager.orchestrator import ManagerOrchestrator
from archon.utils.schemas import TaskResult, FileChange


async def run_sim():
    workspace = Path("test_sim_workspace")
    if workspace.exists():
        import shutil

        shutil.rmtree(workspace)
    workspace.mkdir(exist_ok=True)

    mgr = ManagerOrchestrator(str(workspace))

    # Optional: Mock S3 so it doesn't fail
    mgr.s3_storage.upload_content = AsyncMock(return_value="s3://mocked-url")

    await mgr.initialize()

    goal = "Create a simple Node.js REST API with Express"
    print(f"\n[CLI] User request: {goal}")
    print("\n[ManagerOrchestrator] Parsing goal to ProjectSpec...")

    fake_spec_response = {
        "parsed_json": {
            "goal": "Create a simple Node.js REST API with Express",
            "components": ["backend"],
            "tasks": [
                {
                    "id": "task_backend_1",
                    "description": "Initialize Node.js Express server",
                    "agent": "backend",
                    "dependencies": [],
                }
            ],
            "architecture": {"type": "microservices", "databases": [], "apis": ["REST"]},
        }
    }

    fake_task_result = TaskResult(
        task_id="task_backend_1",
        needs_deliberation=False,
        success=True,
        output={
            "files": [
                {
                    "path": "backend/server.js",
                    "content": "const express = require('express');\nconst app = express();\n\napp.listen(3000, () => {\n  console.log('Server is running on port 3000');\n});",
                },
                {
                    "path": "backend/routes.js",
                    "content": "const express = require('express');\nconst router = express.Router();\n\nrouter.get('/', (req, res) => res.json({status: 'ok'}));\n\nmodule.exports = router;",
                },
                {
                    "path": "backend/package.json",
                    "content": '{\n  "name": "rest-api",\n  "main": "server.js",\n  "dependencies": {\n    "express": "^4.18.2"\n  }\n}',
                },
                {"path": "README.md", "content": "# REST API\nNode.js Express backend API"},
            ]
        },
        files_modified=[],
        quality_score=0.95,
        execution_time_ms=1200,
        model_used="gpt-4-turbo",
        architecture_changes=None,
    )

    class FakeQualityCheck:
        passed = True
        score = 0.9
        checks = {}
        reason = "All good"

    # Patch OpenAIClient
    with patch(
        "archon.manager.orchestrator.ManagerOrchestrator.parse_goal_to_spec", new_callable=AsyncMock
    ) as mock_parse_goal:
        mock_parse_goal.return_value = fake_spec_response["parsed_json"]

        spec = await mgr.parse_goal_to_spec(goal)
        print("Spec generated:")
        print(f"  Tasks: {len(spec.get('tasks', []))}")
        for task in spec.get("tasks", []):
            print(f"    - {task.get('description')} (Agent: {task.get('agent')})")

        print("\nExecuting tasks...")

        # Mock _execute_with_agent and quality_gate.validate
        with (
            patch.object(mgr, "_execute_with_agent", new_callable=AsyncMock) as mock_exec_agent,
            patch.object(mgr.quality_gate, "validate", new_callable=AsyncMock) as mock_validate,
        ):

            mock_exec_agent.return_value = fake_task_result
            mock_validate.return_value = FakeQualityCheck()

            async for event in mgr.execute_plan(spec):
                if event["type"] == "task_completed":
                    print(f"  [✓] {event['agent']} completed: {event['description']}")
                elif event["type"] == "task_failed":
                    print(f"  [✗] Task failed: {event['error']}")
                elif event["type"] == "file_created":
                    print(f"  [📝] Created: {event['path']}")
                elif event.get("type") == "task_started":
                    print(f"  [→] {event['agent']} starting: {event['description']}")
                else:
                    print(f"  [*] Event: {event}")

    print("\n[Verification] Filesystem check...")
    for root, dirs, files in os.walk(workspace):
        for f in files:
            path = Path(root) / f
            rel_path = path.relative_to(workspace)
            if ".archon" not in rel_path.parts:
                print(f"  Found file in workspace: {rel_path}")

    print("\n[Verification] CLI Display simulation...")
    # Simulate UI output for CLI verification
    print(f"backend/server.js")
    print(f"backend/routes.js")
    print(f"backend/package.json")
    print(f"README.md")


if __name__ == "__main__":
    asyncio.run(run_sim())
