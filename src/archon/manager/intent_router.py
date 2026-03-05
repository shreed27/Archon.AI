"""
Intent Router — Analyzes user messages and classifies them into system intents.
"""

import enum
import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel

from archon.utils.logger import get_logger

logger = get_logger(__name__)


class Intent(str, enum.Enum):
    CREATE_PROJECT = "create_project"
    ADD_FEATURE = "add_feature"
    MODIFY_CODE = "modify_code"
    PROJECT_STATUS = "project_status"
    CHAT = "chat"
    UNKNOWN = "unknown"


class RouterResponse(BaseModel):
    intent: Intent
    message: str
    metadata: Dict = {}


from archon.models.model_router import ModelRouter


class IntentRouter:
    """
    Analyzes user natural language messages to determine the system intent.
    """

    def __init__(self):
        self._model_router = ModelRouter()

    async def route(self, user_input: str, history: List[Dict]) -> RouterResponse:
        """
        Classifies the user input into an Intent and provides a friendly message.
        """
        system_prompt = """
You are the Intent Router for ARCHON, an advanced AI Software Engineer.
Your job is to analyze the user's message and classify it into one of the following intents:

- create_project: User wants to build a new project, app, or system from scratch. (e.g., "lets build a todo app", "create a react dashboard")
- add_feature: User wants to add a specific, new functionality to an existing project. (e.g., "add authentication", "implement a navbar")
- modify_code: User wants to change, fix, update, or refactor existing code. (e.g., "change the color of the header", "fix the bug in login.js")
- project_status: User wants to know the current state, task progress, or summary of the project. (e.g., "what's the status?", "show progress")
- chat: General conversation, greetings, questions about how things work, or clarifications that don't trigger a project action. (e.g., "hey archon", "how do you work?")

Return a JSON object with:
1. "intent": The classified intent (string).
2. "message": A friendly, helpful conversational response acknowledging the user's goal.
3. "metadata": Relevant extracted info (e.g., "goal": "todo app", "feature": "auth").
"""
        messages = [
            {"role": "system", "content": system_prompt},
            *(history[-6:] if history else []),
        ]

        try:
            response_text = await self._model_router.generate(messages)
            data = self._parse_json(response_text)

            if not data:
                return self._simulate_route(user_input)

            intent_str = data.get("intent", "chat")
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.CHAT

            return RouterResponse(
                intent=intent,
                message=data.get("message", "I'm on it!"),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.error(f"Error routing intent: {e}")
            return self._simulate_route(user_input)

    def _parse_json(self, text: str) -> Dict:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(text[start : end + 1])
            return {}
        except Exception:
            return {}

    def _simulate_route(self, user_input: str) -> RouterResponse:
        user_input_low = user_input.lower()

        if any(
            word in user_input_low
            for word in ["create", "build", "new project", "generate", "lets make", "lets build"]
        ):
            return RouterResponse(
                intent=Intent.CREATE_PROJECT,
                message=f"Got it. I'll create a project for you. Let's start the planning phase.",
                metadata={"goal": user_input},
            )
        elif any(word in user_input_low for word in ["add", "feature", "implement"]):
            return RouterResponse(
                intent=Intent.ADD_FEATURE,
                message=f"Sure. I'll add that feature for you. Analyzing codebase and planning implementation...",
                metadata={"feature": user_input},
            )
        elif any(word in user_input_low for word in ["status", "how is", "progress", "how are we"]):
            return RouterResponse(
                intent=Intent.PROJECT_STATUS,
                message="Checking the project status for you...",
            )
        elif any(
            word in user_input_low for word in ["change", "modify", "update", "fix", "refactor"]
        ):
            return RouterResponse(
                intent=Intent.MODIFY_CODE,
                message="I'll help you modify the code as requested.",
                metadata={"modification": user_input},
            )
        else:
            return RouterResponse(
                intent=Intent.CHAT,
                message="Hello! I'm Archon. How can I help you with your project today?",
                metadata={},
            )
