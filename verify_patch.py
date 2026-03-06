import os
import asyncio
from pathlib import Path
from archon.manager.file_writer import FileWriter
from archon.utils.schemas import Task, AgentType


class MockResult:
    def __init__(self, output):
        self.output = output


async def main():
    print("=== Testing Patch Edit Workflow ===")
    project_path = str(Path.cwd() / "test_patch_mode")
    os.makedirs(project_path, exist_ok=True)

    writer = FileWriter(project_path)

    # 1. Base Setup
    print("\n[1] Emulating existing file creation...")
    base_result = MockResult(
        {
            "files": [
                {
                    "path": "backend/server.js",
                    "content": "const express = require('express');\nconst app = express();\n\napp.get('/', (req, res) => res.send('OK'));\n",
                }
            ]
        }
    )
    writer.write_artifacts(base_result, agent="backend")

    # Read created file to show initial state
    with open(os.path.join(project_path, "backend/server.js"), "r") as f:
        print(f"Initial server.js:\n{f.read()}")

    # 2. Emulate successful patch application
    print("\n[2] Agent outputting patches for existing file...")
    patch_result = MockResult(
        {
            "patches": [
                {
                    "file": "backend/server.js",
                    "patch": [
                        {
                            "type": "insert",
                            "after": "const app = express();",
                            "content": "const authRoutes = require('./routes/auth');\\napp.use('/auth', authRoutes);",
                        }
                    ],
                    "content": "fallback content if patch failed",
                }
            ]
        }
    )

    writer.write_artifacts(patch_result, agent="integration")

    with open(os.path.join(project_path, "backend/server.js"), "r") as f:
        print(f"Patched server.js:\n{f.read()}")

    # 3. Emulate failing patch and fallback
    print("\n[3] Agent outputting failing patch with fallback...")
    failing_patch_result = MockResult(
        {
            "patches": [
                {
                    "file": "backend/server.js",
                    "patch": [
                        {
                            "type": "replace",
                            "target": "this string doesn't exist!",
                            "content": "replaced",
                        }
                    ],
                    "content": "/* This is the fallback content applied automatically! */",
                }
            ]
        }
    )

    writer.write_artifacts(failing_patch_result, agent="integration")

    with open(os.path.join(project_path, "backend/server.js"), "r") as f:
        print(f"Fallback server.js:\n{f.read()}")


if __name__ == "__main__":
    asyncio.run(main())
