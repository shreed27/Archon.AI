from fastapi import APIRouter

router = APIRouter()

MODELS = [
    {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
    {"id": "deepseek/deepseek-chat", "name": "DeepSeek Chat"},
    {"id": "meta-llama/llama-3-70b-instruct", "name": "Llama 3 70B"},
    {"id": "mistralai/mistral-large", "name": "Mistral Large"},
]


@router.get("/")
async def list_models():
    return MODELS
