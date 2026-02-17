"""
Config Store — persists user configuration as JSON.

Stores settings in ~/Library/Application Support/EOD Reporter/config.json
on macOS. Falls back to ~/.eod-reporter/config.json on other platforms.

Tokens are base64-encoded (not encrypted) for light obfuscation.
"""

from __future__ import annotations

import base64
import json
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional

_APP_NAME = "EOD Reporter"


def _get_config_dir() -> Path:
    """Return the platform-appropriate config directory."""
    system = platform.system()
    if system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    elif system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / _APP_NAME


def _config_path() -> Path:
    """Return the full path to config.json."""
    return _get_config_dir() / "config.json"


# Fields that contain sensitive tokens — stored base64-encoded
_SENSITIVE_FIELDS = {"github_token", "clickup_api_token", "slack_bot_token", "openai_api_key"}

# Default configuration values
DEFAULT_CONFIG: Dict[str, Any] = {
    "github_token": "",
    "github_username": "",
    "clickup_api_token": "",
    "clickup_team_id": "",
    "clickup_user_id": "",
    "slack_bot_token": "",
    "slack_channel": "",
    "slack_user_id": "",
    "slack_display_name": "",
    "slack_icon_url": "",
    "slack_monitor_channels": "",
    "report_hour": 18,
    "report_minute": 0,
    "timezone": "Asia/Kathmandu",
    "log_level": "INFO",
    "app_env": "development",
    # AI summarization
    "openai_api_key": "",
    "ai_model": "gemini-2.0-flash",
    "ai_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "ai_provider": "Google Gemini (Free)",
    # Activity tab customization
    "show_github": True,
    "show_clickup": True,
    "show_slack": True,
    "show_manual": True,
    "show_ai_summary": True,
    "activity_section_order": "github_first",  # or "clickup_first"
    "manual_updates": [],
    "max_commits_per_repo": 10,
    "max_tasks_display": 20,
    "max_comments_display": 10,
}


def _encode(value: str) -> str:
    """Base64-encode a string for light obfuscation."""
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _decode(value: str) -> str:
    """Decode a base64-encoded string."""
    try:
        return base64.b64decode(value.encode("ascii")).decode("utf-8")
    except Exception:
        return value  # return as-is if not valid base64


def load_config() -> Dict[str, Any]:
    """
    Load configuration from disk.

    Returns DEFAULT_CONFIG merged with any saved values.
    Missing keys get default values; extra keys are preserved.
    """
    config = dict(DEFAULT_CONFIG)
    path = _config_path()

    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for key, value in raw.items():
                if key in _SENSITIVE_FIELDS and isinstance(value, str) and value:
                    config[key] = _decode(value)
                else:
                    config[key] = value
        except (json.JSONDecodeError, OSError):
            pass  # corrupt file — use defaults

    return config


def save_config(config: Dict[str, Any]) -> None:
    """
    Persist configuration to disk.

    Sensitive fields are base64-encoded before writing.
    """
    config_dir = _get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    to_write: Dict[str, Any] = {}
    for key, value in config.items():
        if key in _SENSITIVE_FIELDS and isinstance(value, str) and value:
            to_write[key] = _encode(value)
        else:
            to_write[key] = value

    _config_path().write_text(
        json.dumps(to_write, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def import_from_dotenv(dotenv_path: str | Path) -> Optional[Dict[str, Any]]:
    """
    Import settings from an existing .env file.

    Returns the imported config dict, or None if the file doesn't exist.
    """
    path = Path(dotenv_path)
    if not path.exists():
        return None

    imported: Dict[str, Any] = dict(DEFAULT_CONFIG)
    env_map = {
        "GITHUB_TOKEN": "github_token",
        "GITHUB_USERNAME": "github_username",
        "CLICKUP_API_TOKEN": "clickup_api_token",
        "CLICKUP_TEAM_ID": "clickup_team_id",
        "CLICKUP_USER_ID": "clickup_user_id",
        "SLACK_BOT_TOKEN": "slack_bot_token",
        "SLACK_CHANNEL": "slack_channel",
        "SLACK_USER_ID": "slack_user_id",
        "SLACK_DISPLAY_NAME": "slack_display_name",
        "SLACK_ICON_URL": "slack_icon_url",
        "REPORT_HOUR": "report_hour",
        "REPORT_MINUTE": "report_minute",
        "TIMEZONE": "timezone",
        "LOG_LEVEL": "log_level",
        "APP_ENV": "app_env",
    }

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key in env_map:
                config_key = env_map[key]
                # Convert numeric fields
                if config_key in ("report_hour", "report_minute"):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                elif config_key == "clickup_user_id":
                    pass  # keep as string in our config
                imported[config_key] = value
    except OSError:
        return None

    return imported


def config_exists() -> bool:
    """Check if a config file already exists."""
    return _config_path().exists()


def get_config_path() -> Path:
    """Return the config file path (for display purposes)."""
    return _config_path()
