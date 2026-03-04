from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from ..database.db import get_db
from ..database.models import User
from ..services.openrouter_client import OpenRouterClient
from ..services.usage_tracker import UsageTracker
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio

# Assuming we can import Archon components
# We might need to adjust PYTHONPATH or use a wrapper
try:
    from archon.manager.orchestrator import ManagerOrchestrator
except ImportError:
    ManagerOrchestrator = None

router = APIRouter()


class ChatRequest(BaseModel):
    messages: List[dict]
    model: str
    project_path: Optional[str] = "."


@router.post("/completions")
async def chat_completions(request: ChatRequest, db: Session = Depends(get_db)):
    # Simple non-streaming completion for general chat
    client = OpenRouterClient()
    response = client.generate(request.messages, request.model)

    # Track usage (simplified)
    usage = response.get("usage", {"total_tokens": 0})
    tracker = UsageTracker(db)
    # email = "user@example.com" # Get from token
    # tracker.track_usage(email, usage.get("total_tokens", 0))

    return response


@router.get("/stream")
async def chat_stream(
    req: Request, prompt: str, model: str, project_path: str = ".", db: Session = Depends(get_db)
):
    """
    Main streaming endpoint using SSE.
    """
    client = OpenRouterClient()
    tracker = UsageTracker(db)

    async def event_generator():
        if ManagerOrchestrator is None:
            yield {
                "data": json.dumps({"type": "error", "content": "Archon Orchestrator not found"})
            }
            return

        orchestrator = ManagerOrchestrator(project_path)
        await orchestrator.initialize()

        # We need a proper way to stream through orchestrator
        # Adapting stream_conversational_input
        history = [{"role": "user", "content": prompt}]

        async for update in orchestrator.stream_conversational_input(prompt, history):
            if await req.is_disconnected():
                break

            yield {"data": json.dumps(update)}

            # If it yields a spec, we might need to trigger execution
            if update.get("type") == "done" and update.get("action") == "execute_task":
                spec = update.get("spec")
                yield {"data": json.dumps({"type": "status", "content": "Starting execution..."})}

                async for step in orchestrator.execute_plan(spec):
                    if await req.is_disconnected():
                        break
                    yield {"data": json.dumps(step)}

    return EventSourceResponse(event_generator())
