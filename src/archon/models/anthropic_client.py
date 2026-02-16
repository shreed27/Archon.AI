"""
Anthropic Client - Claude integration.
"""

import os
from typing import List, Dict, Optional
from anthropic import AsyncAnthropic


class AnthropicClient:
    """
    Client for Anthropic Claude models.
    Supports Claude 3 Opus, Sonnet, and Haiku.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")

        self.client = AsyncAnthropic(api_key=self.api_key)
        self.default_model = "claude-3-opus-20240229"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system: Optional[str] = None,
    ) -> str:
        """
        Send chat completion request.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to claude-3-opus)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            system: System prompt

        Returns:
            Generated text response
        """
        model = model or self.default_model

        try:
            # Convert messages format if needed
            formatted_messages = self._format_messages(messages)

            response = await self.client.messages.create(
                model=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
            )

            return response.content[0].text

        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {str(e)}")

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages for Anthropic API."""
        formatted = []
        for msg in messages:
            role = msg["role"]
            # Anthropic uses "user" and "assistant" roles
            if role == "system":
                # System messages should be passed separately
                continue
            formatted.append({"role": role, "content": msg["content"]})
        return formatted

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count tokens for
            model: Model to use for counting

        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        # Anthropic uses similar tokenization to GPT models
        return len(text) // 4

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
        ]

    def get_model_context_window(self, model: str) -> int:
        """Get context window size for a model."""
        context_windows = {
            "claude-3-opus-20240229": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
            "claude-2.1": 200000,
            "claude-2.0": 100000,
        }
        return context_windows.get(model, 100000)
