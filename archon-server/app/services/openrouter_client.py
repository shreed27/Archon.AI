import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


class OpenRouterClient:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://archon.ai",  # Optional
            "X-Title": "Archon AI",  # Optional
            "Content-Type": "application/json",
        }

    def generate(self, messages, model, stream=False):
        payload = {"model": model, "messages": messages, "stream": stream}

        if stream:
            return self._stream_response(payload)
        else:
            return self._sync_response(payload)

    def _sync_response(self, payload):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload
            )
            data = response.json()
            print("OpenRouter raw response:", data)

            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                content = message.get("content", "")

                if not content:
                    content = "Model returned an empty response."

                data["choices"][0]["message"]["content"] = content
                return data

            elif "error" in data:
                error_msg = data["error"].get("message", "Unknown OpenRouter error")
                print(f"OpenRouter error: {error_msg}")
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I'm Archon, i think Something went wrong while contacting the model. Please try again."
                            }
                        }
                    ]
                }

            else:
                print(f"Unexpected OpenRouter response: {data}")
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "I'm Archon, i think Something went wrong while contacting the model. Please try again."
                            }
                        }
                    ]
                }

        except Exception as e:
            print("OpenRouter exception:", str(e))
            return {
                "choices": [
                    {
                        "message": {
                            "content": "I'm Archon, i think Something went wrong while contacting the model. Please try again."
                        }
                    }
                ]
            }

    def _stream_response(self, payload):
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions", headers=self.headers, json=payload, stream=True
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[len("data: ") :]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                yield data
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            print("OpenRouter stream parse exception:", str(e))
                            continue
        except Exception as e:
            print("OpenRouter stream exception:", str(e))
            yield {
                "choices": [
                    {
                        "delta": {
                            "content": "\nI'm Archon, i think Something went wrong while contacting the model. Please try again."
                        }
                    }
                ]
            }
