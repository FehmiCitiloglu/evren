from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import yaml

# Load .env file automatically
load_dotenv()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from config.yaml or return sensible defaults."""
    default_path = Path("config.yaml")
    target_path = Path(config_path) if config_path else default_path

    if target_path.exists():
        with open(target_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data

    # Default fallback
    return {
        "agent": {
            "name": "EvrenAgent",
            "system_prompt": "You are EvrenAgent, an autonomous AI assistant.",
            "default_provider": "evren",
            "max_iterations": 15,
            "temperature": 0.7,
            "stream": True,
        },
        "providers": {
            "evren": {
                "base_url": "https://evren-llmapi.ssyz.org.tr/v1",
                "default_model": "glm-5.3",
            },
            "llmtr": {
                "base_url": "https://llmtr.com/v1",
                "default_model": "evren/glm-5.3-fp8",
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4o",
            },
        },
        "mcp_servers": {},
        "skills": {
            "directory": "skills",
            "autoload_builtins": True,
            "active_skills": ["code_assistant", "computer-use"],
        },
        "plugins": {"directory": "plugins", "autoload_builtins": True},
    }
