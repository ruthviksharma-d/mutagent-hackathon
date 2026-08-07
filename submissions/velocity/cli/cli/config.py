"""
Configuration management for PromptShield CLI.
Reads environment variables and optional user configuration file.
"""
import os
import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".promptshield"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_BACKEND_URL = os.getenv("PROMPTSHIELD_BACKEND_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = int(os.getenv("PROMPTSHIELD_TIMEOUT", "30"))


def load_config() -> dict:
    config = {
        "backend_url": DEFAULT_BACKEND_URL,
        "timeout": DEFAULT_TIMEOUT,
        "api_token": os.getenv("PROMPTSHIELD_API_TOKEN", ""),
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception:
            pass
    return config


def save_config(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    current = load_config()
    current.update(data)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
