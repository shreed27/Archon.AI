"""
OpenAI Client - GPT-4 integration.
"""

import os
from typing import List, Dict, Optional, AsyncIterator
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion


class OpenAIClient:
    """
    Client for OpenAI GPT models.
    Supports GPT-4, GPT-4 Turbo, and streaming responses.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.default_model = "gpt-4-turbo-preview"

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_prompt: str = "You are a helpful AI assistant.",
    ) -> Dict[str, Any]:
        """
        Complete a prompt and optionally parse JSON.

        Args:
            prompt: User prompt
            model: Model name
            system_prompt: System instruction

        Returns:
            Dict containing 'content' and optional 'parsed_json'
        """
        import json

        model = model or self.default_model

        # Helper to extract JSON from markdown code blocks
        def extract_json(text):
            try:
                # Try direct parse
                return json.loads(text)
            except:
                pass

            # Try finding ```json block
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end != -1:
                    try:
                        return json.loads(text[start:end].strip())
                    except:
                        pass
            # Try finding { ... }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except:
                    pass
            return {}

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        content = await self.chat(messages, model=model)

        parsed = extract_json(content)

        return {"content": content, "parsed_json": parsed}

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Send chat completion request.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to gpt-4-turbo-preview)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            Generated text response
        """
        model = model or self.default_model

        try:
            if stream:
                return await self._chat_stream(messages, model, temperature, max_tokens)
            else:
                response: ChatCompletion = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,  # type: ignore
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response.choices[0].message.content or ""

        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    async def _chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
    ) -> str:
        """Handle streaming response."""
        full_response = ""

        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content

            return full_response

        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {str(e)}")

    async def get_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Get text embedding.

        Args:
            text: Text to embed
            model: Embedding model to use

        Returns:
            Embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding

        except Exception as e:
            raise RuntimeError(f"OpenAI embedding error: {str(e)}")

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
        # In production, use tiktoken library for accurate counting
        return len(text) // 4

    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return [
            "gpt-4-turbo-preview",
            "gpt-4",
            "gpt-4-32k",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
