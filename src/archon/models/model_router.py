import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncIterator


class ModelRouter:
    """
    Unified Model Router for Archon via OpenRouter.
    Manages model selection and configuration.
    """

    DEFAULT_CONFIG_PATH = Path(os.path.expanduser("~/.archon/config.json"))

    MODEL_MAP = {
        "claude": "anthropic/claude-3.5-sonnet",
        "deepseek": "deepseek/deepseek-chat",
        "llama": "meta-llama/llama-3-70b-instruct",
        "mistral": "mistralai/mistral-large",
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()

        # Load from config or defaults
        self.current_model = self.config.get("model", "deepseek")
        self._provider = None  # Lazy loaded

    def _load_config(self) -> Dict:
        """Load persistent config from home directory."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        """Save current model to persistent config."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config["model"] = self.current_model

        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def set_model(self, model_alias: str):
        """
        Update the current model.
        """
        if model_alias in self.MODEL_MAP or "/" in model_alias:
            self.current_model = model_alias
            self.save_config()
            return True
        return False

    def _get_provider(self):
        if self._provider is None:
            from archon.models.providers.openrouter_provider import OpenRouterProvider

            self._provider = OpenRouterProvider()
        return self._provider

    def _get_full_model_id(self) -> str:
        return self.MODEL_MAP.get(self.current_model, self.current_model)

    async def generate(self, messages: Any) -> str:
        """
        Route messages to OpenRouter.
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        provider = self._get_provider()
        model_id = self._get_full_model_id()
        return await provider.generate(messages, model=model_id)

    async def stream_generate(self, messages: Any) -> AsyncIterator[str]:
        """
        Route streaming messages to OpenRouter.
        """
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]

        provider = self._get_provider()
        model_id = self._get_full_model_id()

        async for chunk in provider.stream_generate(messages, model=model_id):
            yield chunk

    def get_available_models(self) -> Dict[str, str]:
        return self.MODEL_MAP

    def get_status(self) -> str:
        return f"Model set to {self.current_model} ({self._get_full_model_id()})"
