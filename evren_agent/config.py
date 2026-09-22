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


def save_config(config_data: Dict[str, Any], config_path: Optional[str] = None) -> Path:
    """Save configuration dictionary back to YAML file."""
    default_path = Path("config.yaml")
    target_path = Path(config_path) if config_path else default_path
    with open(target_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return target_path


def get_mcp_servers_from_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve mcp_servers dictionary from config.yaml."""
    cfg = load_config(config_path)
    servers = cfg.get("mcp_servers", {})
    return servers if isinstance(servers, dict) else {}


def add_mcp_server_to_config(
    name: str,
    server_config: Dict[str, Any],
    config_path: Optional[str] = None,
) -> Path:
    """Add or update an MCP server configuration in config.yaml."""
    cfg = load_config(config_path)
    if "mcp_servers" not in cfg or not isinstance(cfg["mcp_servers"], dict):
        cfg["mcp_servers"] = {}
    cfg["mcp_servers"][name] = server_config
    return save_config(cfg, config_path)


def remove_mcp_server_from_config(
    name: str,
    config_path: Optional[str] = None,
) -> bool:
    """Remove an MCP server from config.yaml. Returns True if removed, False if not found."""
    cfg = load_config(config_path)
    servers = cfg.get("mcp_servers", {})
    if isinstance(servers, dict) and name in servers:
        del servers[name]
        save_config(cfg, config_path)
        return True
    return False
