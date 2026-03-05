import os
import json
from pathlib import Path
from typing import Dict, Any

from archon.utils.logger import get_logger

logger = get_logger(__name__)


from archon.models.model_router import ModelRouter


class ProjectStructurePlanner:
    """
    ProjectStructurePlanner layer for Archon.
    Generates a project directory structure before agents begin writing files,
    improving stability for large applications.
    """

    def __init__(self, project_path: str, model_router=None):
        self.project_path = Path(project_path).resolve()
        self.model_router = model_router or ModelRouter()

    async def generate_structure(self, spec: Dict) -> Dict[str, Any]:
        """
        Parses the ProjectSpec and generates a structured directory tree representing
        the project's initial layout.
        """
        logger.info("ProjectStructurePlanner: Generating project structure.")
        goal = spec.get("goal", "")
        components = spec.get("components", [])

        prompt = f"""
You are the Architecture Planner of ARCHON.
Based on the following project specification, generate an initial structured directory tree.

Goal: {goal}
Components: {', '.join(components)}

Output ONLY a JSON format where keys are top-level directories and values are lists of files or subdirectories (subdirectories should end with '/'):
{{
    "backend/": [
        "server.js",
        "routes/",
        "models/"
    ],
    "frontend/": [
        "App.jsx",
        "components/",
        "pages/"
    ],
    "docs/": [],
    "config/": []
}}
"""

        try:
            response_text = await self.model_router.generate(prompt)
            try:
                start = response_text.find("{")
                end = response_text.rfind("}")
                if start != -1 and end != -1:
                    structure = json.loads(response_text[start : end + 1])
                else:
                    structure = {}
            except Exception:
                structure = {}
        except Exception as e:
            logger.error(f"Error generating project structure: {e}")
            structure = {}

        return structure

    def create_directories(self, structure: Dict[str, Any]):
        """
        Creates the given directories in the workspace before agents run.
        Ensures the predefined directory tree exists.
        """
        logger.info("ProjectStructurePlanner: Creating predefined directories in workspace.")
        for root_dir, items in structure.items():
            dir_name = root_dir.strip("/")
            dir_path = self.project_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

            for item in items:
                if item.endswith("/"):
                    sub_dir_name = item.strip("/")
                    (dir_path / sub_dir_name).mkdir(parents=True, exist_ok=True)
