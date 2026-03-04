import os
import json
import webbrowser
from pathlib import Path
import requests

SESSION_FILE = Path.home() / ".archon" / "session.json"
CONFIG_FILE = Path.home() / ".archon" / "config.json"
SERVER_URL = os.getenv("ARCHON_SERVER_URL", "http://localhost:8000")


def get_session():
    if SESSION_FILE.exists():
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return None


def save_session(token):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump({"token": token}, f)


def get_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"model": "Claude 3.5 Sonnet"}


def save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


def login():
    # In a real app, this would open a browser to a Google Auth URL
    # For now, we'll simulate the flow
    print("Opening browser for Google Login...")
    # webbrowser.open(f"{SERVER_URL}/auth/google/login")

    # After login, the browser would redirect to a page that gives a token
    # or the CLI would poll the server

    # Mock token for demonstration
    mock_token = "mock-jwt-token"

    # We call our backend /auth/google with a mock token
    response = requests.post(f"{SERVER_URL}/auth/google", json={"token": "mock-google-token"})
    if response.status_code == 200:
        token = response.json().get("token")
        save_session(token)
        return token
    else:
        print("Login failed.")
        return None
