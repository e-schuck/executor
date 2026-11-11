"""Configuration manager for Windows Startup Launcher."""

import json
import os
import sys
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "auto_start": True,
    "minimize_to_tray": True,
    "commands": [
        {
            "name": "OmniRoute",
            "command": "npx",
            "args": "omniroute",
            "workdir": "C:\\Users\\evandro",
            "enabled": True,
            "delay_seconds": 5,
            "run_minimized": True,
        },
        {
            "name": "Qdrant",
            "command": "D:\\Apps\\Qdrant\\qdrant.exe",
            "args": "",
            "workdir": "D:\\Apps\\Qdrant",
            "enabled": True,
            "delay_seconds": 0,
            "run_minimized": False,
        },
    ],
}


def get_app_dir() -> str:
    """Return the directory where the executable or script lives."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_config_path() -> str:
    return os.path.join(get_app_dir(), "config.json")


def load_config() -> dict[str, Any]:
    """Load config from JSON file; create default if missing."""
    path = get_config_path()
    if not os.path.exists(path):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all expected keys exist
        if "auto_start" not in data:
            data["auto_start"] = DEFAULT_CONFIG["auto_start"]
        if "minimize_to_tray" not in data:
            data["minimize_to_tray"] = DEFAULT_CONFIG["minimize_to_tray"]
        if "commands" not in data:
            data["commands"] = []
        return data
    except (json.JSONDecodeError, OSError):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """Persist configuration to JSON file."""
    path = get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)