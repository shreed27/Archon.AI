"""
OpenRouter Provider - Unified Model Access
"""

import os
import json
from typing import List, Dict, Optional, AsyncIterator
import httpx


class OpenRouterProvider:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def generate(self, messages: List[Dict[str, str]], model: str) -> str:
        if not self.api_key:
            return self._missing_key_message()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://archon.ai",
                        "X-Title": "Archon AI",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                print("OpenRouter raw response:", data)

                if "choices" in data and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message", {})
                    content = message.get("content", "")

                    if not content:
                        content = "Model returned an empty response."

                    return content

                elif "error" in data:
                    error_msg = data["error"].get("message", "Unknown OpenRouter error")
                    print(f"OpenRouter error: {error_msg}")
                    return "I'm Archon, i think Something went wrong while contacting the model. Please try again."

                else:
                    print(f"Unexpected OpenRouter response: {data}")
                    return "I'm Archon, i think Something went wrong while contacting the model. Please try again."

        except Exception as e:
            print("OpenRouter exception:", str(e))
            return "I'm Archon, i think Something went wrong while contacting the model. Please try again."

    async def stream_generate(
        self, messages: List[Dict[str, str]], model: str
    ) -> AsyncIterator[str]:
        if not self.api_key:
            yield self._missing_key_message()
            return

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://archon.ai",
                        "X-Title": "Archon AI",
                    },
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": True,
                    },
                    timeout=60.0,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or line == "keep-alive":
                            continue
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and len(data["choices"]) > 0:
                                    chunk = data["choices"][0].get("delta", {}).get("content", "")
                                    if chunk:
                                        yield chunk
                            except (json.JSONDecodeError, KeyError):
                                continue
        except Exception as e:
            print("OpenRouter stream exception:", str(e))
            yield "\nI'm Archon, i think Something went wrong while contacting the model. Please try again."

    def _missing_key_message(self) -> str:
        return (
            "OpenRouter API key not found.\n\n"
            "To use Archon, set your key:\n\n"
            "export OPENROUTER_API_KEY=your_key\n\n"
            "Get a free key at:\n"
            "https://openrouter.ai/keys"
        )
