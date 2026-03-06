import os
import asyncio
from pathlib import Path
from archon.intelligence.code_retriever import CodeRetriever
from archon.manager.file_writer import FileWriter
from archon.utils.schemas import Task, AgentType
from archon.manager.orchestrator import ManagerOrchestrator
from pydantic import BaseModel


class MockResult(BaseModel):
    output: dict


async def main():
    print("=== Testing CodeRetriever Integration ===")
    project_path = str(Path.cwd() / "test_retriever_proj")
    os.makedirs(project_path, exist_ok=True)

    # 1. Init FileWriter (which has CodeRetriever)
    writer = FileWriter(project_path)

    # 2. Mock some written files
    print("\n[1] Emulating file writes (Embedding code)...")
    mock_result = MockResult(
        output={
            "files": [
                {
                    "path": "backend/routes/users.js",
                    "content": "const express = require('express');\nconst router = express.Router();\nrouter.get('/users', (req, res) => res.json({}));\nmodule.exports = router;",
                },
                {
                    "path": "backend/controllers/userController.js",
                    "content": "const listUsers = (req, res) => { res.json([{id: 1, name: 'Alice'}]); };\nmodule.exports = { listUsers };",
                },
                {
                    "path": "frontend/App.js",
                    "content": "import React from 'react';\nfunction App() { return <div>Basic UI</div>; }\nexport default App;",
                },
            ]
        }
    )

    # This will trigger writer.code_retriever.embed_file under the hood
    writer.write_artifacts(mock_result, agent="Backend Agent")
    print("Files embedded successfully.")

    # Wait briefly for ChromaDB async writes if any
    await asyncio.sleep(1)

    # 3. Emulate ManagerOrchestrator searching during an agent task
    print("\n[2] Testing retrieval based on semantic task description...")
    retriever = CodeRetriever(project_path)

    sample_task_desc = (
        "Implement the get user endpoint using the express router and userController logic."
    )
    print(f"Query: {sample_task_desc}\n")

    relevant_files = retriever.search(sample_task_desc, top_k=2)

    print("=== Retrieved Code Snippets ===")
    snippet_text = "\nRelevant project files:\n\n"
    for f in relevant_files:
        snippet_text += f"{f['path']} \n```\n{f['content']}\n```\n\n"

    print(snippet_text)


if __name__ == "__main__":
    asyncio.run(main())
