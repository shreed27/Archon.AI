"""
Amazon Bedrock Client - Integration for Claude, Llama, and Titan models.
"""

import os
import json
import boto3
from typing import List, Dict, Optional, Any
from archon.utils.logger import get_logger

logger = get_logger(__name__)


class BedrockClient:
    """
    Client for Amazon Bedrock models.
    Supports Claude 3, Llama 3, and Titan via the Converse API.
    """

    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")

        # Initialize boto3 client
        session_kwargs = {
            "region_name": self.region_name,
        }
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.client = boto3.client("bedrock-runtime", **session_kwargs)

    async def complete(
        self,
        prompt: str,
        model: str,
        system_prompt: str = "You are a helpful AI assistant.",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Complete a prompt using Bedrock Converse API.
        """
        messages = [{"role": "user", "content": [{"text": prompt}]}]

        system = [{"text": system_prompt}]

        inference_config = {
            "maxTokens": max_tokens,
            "temperature": temperature,
            "topP": 0.9,
        }

        try:
            # Note: Converse API is synchronous in boto3, but we wrap it for consistency
            # In a production async environment, use a thread pool or aiobotocore
            response = self.client.converse(
                modelId=model,
                messages=messages,
                system=system,
                inferenceConfig=inference_config,
            )

            content = response["output"]["message"]["content"][0]["text"]

            # Extract JSON if present (similar to OpenAIClient)
            parsed = self._extract_json(content)

            return {"content": content, "parsed_json": parsed, "usage": response.get("usage", {})}

        except Exception as e:
            logger.error(f"Bedrock API error: {str(e)}")
            raise RuntimeError(f"Bedrock API error: {str(e)}")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Helper to extract JSON from markdown code blocks."""
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

    async def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4
