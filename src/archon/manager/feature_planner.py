import os
import json
from pathlib import Path
from typing import Dict, Any, List

from archon.utils.logger import get_logger

logger = get_logger(__name__)


class FeaturePlanner:
    """
    FeaturePlanner layer for Archon.
    Analyzes an existing project and generates tasks to add a new feature without overwriting existing codebase.
    Uses CodeRetriever for impact analysis.
    """

    def __init__(self, project_path: str, code_retriever, model_router=None):
        self.project_path = Path(project_path).resolve()
        self.code_retriever = code_retriever
        self.model_router = model_router

    async def generate_feature_plan(
        self, feature_description: str, codebase_index, project_memory
    ) -> Dict[str, Any]:
        """
        Generates a structured execution plan for adding a feature.
        """
        logger.info(f"FeaturePlanner: Generating plan for feature - {feature_description}")

        # 1. Impact Analysis using CodeRetriever
        impacted_files_context = ""
        try:
            if self.code_retriever:
                relevant_files = self.code_retriever.search(feature_description, top_k=5)
                if relevant_files:
                    impacted_files_context = "Potentially Impacted Code Files:\n\n"
                    for f in relevant_files:
                        impacted_files_context += f"{f['path']}\n```\n{f['content']}\n```\n\n"
        except Exception as e:
            logger.error(f"Error during impact analysis: {e}")

        # 2. Build prompt
        pm_summary = project_memory.get_summary() if project_memory else ""

        prompt = f"""
You are the Feature Architecture Planner of ARCHON.
Your goal is to plan tasks to ADD a new feature to an EXISTING project. Do not regenerate the entire project.

Feature Request: {feature_description}

{impacted_files_context}

Project Memory Summary:
{pm_summary}

Output ONLY a JSON format with a goal, components to modify/add, tasks, and architecture.
{{
    "goal": "{feature_description}",
    "components": ["e.g. backend api", "frontend ui"],
    "tasks": [
        {{
            "id": "task_001",
            "description": "Modify existing file X to add feature Y. Provide clear instructions to use complete modifications.",
            "agent": "backend",
            "dependencies": []
        }}
    ],
    "architecture": {{
        "type": "existing",
        "modifications": []
    }}
}}
"""

        try:
            if self.model_router:
                response_text = await self.model_router.generate(prompt)
                try:
                    start = response_text.find("{")
                    end = response_text.rfind("}")
                    if start != -1 and end != -1:
                        spec = json.loads(response_text[start : end + 1])
                    else:
                        spec = {}
                except Exception:
                    spec = {}
            else:
                logger.warning("No ModelRouter provided. Returning mock feature spec.")
                spec = {
                    "goal": feature_description,
                    "components": ["mock_component"],
                    "tasks": [
                        {
                            "id": "mock_1",
                            "description": "Add feature to existing file",
                            "agent": "integration",
                            "dependencies": [],
                        }
                    ],
                    "architecture": {"type": "mock", "modifications": []},
                }
        except Exception as e:
            logger.error(f"Error generating feature spec: {e}")
            spec = {
                "goal": feature_description,
                "components": ["error_component"],
                "tasks": [],
                "architecture": {},
            }

        return spec
