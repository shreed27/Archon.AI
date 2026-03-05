import json
from typing import Dict, List, Tuple
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class ProjectPlanner:
    """
    ProjectPlanner - Converts user requests into structured project specifications.
    Enforces strict JSON output and provides safe fallbacks.
    """

    def __init__(self, model_router=None):
        self.model_router = model_router

    async def generate_spec(self, user_message: str, project_context: str = "") -> Dict:
        """
        Generate a structured project specification from a user message.
        """
        prompt = f"""
You are the project planning system for an AI software engineer.
Convert the user request into a structured project specification.

Project Context:
{project_context}

User request:
{user_message}

Return ONLY JSON.

Format:
{{
  "goal": "short description of the project",
  "tasks": [
    {{
      "id": "task_1",
      "agent": "ArchitectAgent",
      "description": "Design overall system architecture",
      "dependencies": []
    }},
    {{
      "id": "task_2",
      "agent": "BackendAgent",
      "description": "Create backend API",
      "dependencies": ["task_1"]
    }},
    {{
      "id": "task_3",
      "agent": "FrontendAgent",
      "description": "Build frontend interface",
      "dependencies": ["task_1", "task_2"]
    }}
  ],
  "architecture": {{
    "type": "webapp",
    "databases": [],
    "apis": []
  }}
}}
"""
        try:
            if self.model_router:
                response = await self.model_router.generate(prompt)
                logger.info(f"Planner raw response: {response}")
                print("Planner raw response:", response)
                return self.parse_planner_response(response, user_message)
            else:
                logger.warning("No model router provided, using fallback plan.")
                return self.fallback_plan(user_message)
        except Exception as e:
            logger.error(f"Planner error: {e}")
            return self.fallback_plan(user_message)

    def parse_planner_response(self, response: str, user_message: str) -> Dict:
        """
        Safely parse JSON response from the model.
        """
        try:
            # Basic cleanup of markdown markers if present
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()

            start = clean_response.find("{")
            end = clean_response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(clean_response[start : end + 1])
            else:
                raise ValueError("No JSON object found")

            goal = data.get("goal")
            tasks = data.get("tasks", [])

            if not goal:
                data["goal"] = user_message

            if not tasks:
                logger.warning("Planner produced empty tasks. Using fallback.")
                return self.fallback_plan(user_message)

            return data
        except Exception as e:
            logger.error(f"Planner JSON parse failed: {e}. Raw response: {response}")
            print("Planner JSON parse failed. Raw response:", response)
            return self.fallback_plan(user_message)

    def fallback_plan(self, user_message: str) -> Dict:
        """
        Produce a default plan when AI generation or parsing fails.
        """
        return {
            "goal": user_message,
            "tasks": [
                {
                    "id": "fallback_1",
                    "agent": "ArchitectAgent",
                    "description": "Design system architecture",
                    "dependencies": [],
                },
                {
                    "id": "fallback_2",
                    "agent": "BackendAgent",
                    "description": "Implement backend API",
                    "dependencies": ["fallback_1"],
                },
                {
                    "id": "fallback_3",
                    "agent": "FrontendAgent",
                    "description": "Create frontend interface",
                    "dependencies": ["fallback_1", "fallback_2"],
                },
            ],
            "architecture": {"type": "fallback", "databases": [], "apis": []},
        }
