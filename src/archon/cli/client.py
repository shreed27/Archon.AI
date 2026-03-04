import requests
import json
import httpx
from .auth import get_session, SERVER_URL


class ArchonClient:
    def __init__(self):
        session = get_session()
        self.token = session.get("token") if session else None
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    async def stream_chat(self, prompt, model, project_path="."):
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{SERVER_URL}/chat/stream",
                params={"prompt": prompt, "model": model, "project_path": project_path},
                headers=self.headers,
                timeout=None,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[len("data: ") :])
                        yield data

    def list_models(self):
        response = requests.get(f"{SERVER_URL}/models/", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []

    def get_me(self):
        response = requests.get(f"{SERVER_URL}/auth/me", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return None
