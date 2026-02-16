"""
Google Client - Gemini integration.
"""

import os
from typing import List, Dict, Optional
import google.generativeai as genai


class GoogleClient:
    """
    Client for Google Gemini models.
    Supports Gemini Pro and Gemini Pro Vision.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided")

        genai.configure(api_key=self.api_key)
        self.default_model = "gemini-pro"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send chat completion request.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to gemini-pro)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        model_name = model or self.default_model

        try:
            # Initialize model
            gemini_model = genai.GenerativeModel(model_name)

            # Convert messages to Gemini format
            prompt = self._format_messages(messages)

            # Generate response
            generation_config = genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            response = await gemini_model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )

            return response.text

        except Exception as e:
            raise RuntimeError(f"Google API error: {str(e)}")

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages for Gemini API.
        Gemini uses a simpler prompt format.
        """
        formatted_parts = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                formatted_parts.append(f"System: {content}")
            elif role == "user":
                formatted_parts.append(f"User: {content}")
            elif role == "assistant":
                formatted_parts.append(f"Assistant: {content}")

        return "\n\n".join(formatted_parts)

    async def chat_with_history(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """
        Send chat with conversation history.

        Args:
            messages: List of message dictionaries
            model: Model to use
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        model_name = model or self.default_model

        try:
            gemini_model = genai.GenerativeModel(model_name)

            # Start chat session
            chat = gemini_model.start_chat(history=[])

            # Convert messages to chat format
            for msg in messages[:-1]:  # All but last message
                if msg["role"] == "user":
                    chat.send_message(msg["content"])

            # Send final message and get response
            last_message = messages[-1]["content"]
            response = await chat.send_message_async(last_message)

            return response.text

        except Exception as e:
            raise RuntimeError(f"Google chat error: {str(e)}")

    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count tokens for text.

        Args:
            text: Text to count tokens for
            model: Model to use for counting

        Returns:
            Token count
        """
        model_name = model or self.default_model

        try:
            gemini_model = genai.GenerativeModel(model_name)
            result = gemini_model.count_tokens(text)
            return result.total_tokens

        except Exception:
            # Fallback estimation
            return len(text) // 4

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    def get_model_context_window(self, model: str) -> int:
        """Get context window size for a model."""
        context_windows = {
            "gemini-pro": 32760,
            "gemini-pro-vision": 16384,
            "gemini-1.5-pro": 1000000,
            "gemini-1.5-flash": 1000000,
        }
        return context_windows.get(model, 32760)
