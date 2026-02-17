"""
Service Bridge — injects local config into the environment so that
the existing ``app.config.Settings`` singleton picks up the values.

The bridge sets ``os.environ`` BEFORE any ``app.*`` module is imported.
This means the Pydantic Settings object, module-level headers, and
Slack client all initialise with the correct tokens automatically —
no patching or monkey-business required.

Usage (in desktop/main.py)::

    from desktop.service_bridge import init_env_from_config
    init_env_from_config()          # must be called FIRST
    from app.scheduler import ...   # safe to import now
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure the project root is on sys.path so ``app.*`` imports work
# when running from the desktop/ directory.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from desktop.config_store import load_config


# Mapping: config_store key → environment variable name
_ENV_MAP: Dict[str, str] = {
    "github_token": "GITHUB_TOKEN",
    "github_username": "GITHUB_USERNAME",
    "clickup_api_token": "CLICKUP_API_TOKEN",
    "clickup_team_id": "CLICKUP_TEAM_ID",
    "clickup_user_id": "CLICKUP_USER_ID",
    "slack_bot_token": "SLACK_BOT_TOKEN",
    "slack_channel": "SLACK_CHANNEL",
    "slack_user_id": "SLACK_USER_ID",
    "slack_display_name": "SLACK_DISPLAY_NAME",
    "slack_icon_url": "SLACK_ICON_URL",
    "report_hour": "REPORT_HOUR",
    "report_minute": "REPORT_MINUTE",
    "timezone": "TIMEZONE",
    "log_level": "LOG_LEVEL",
    "app_env": "APP_ENV",
}


def init_env_from_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load the local config and inject values into ``os.environ``.

    Must be called **before** importing any ``app.*`` module.

    Args:
        config: Pre-loaded config dict. If ``None``, loads from disk.

    Returns:
        The config dict that was applied.
    """
    if config is None:
        config = load_config()

    for config_key, env_var in _ENV_MAP.items():
        value = config.get(config_key, "")
        str_value = str(value)
        if str_value:
            os.environ[env_var] = str_value
        elif env_var in os.environ:
            del os.environ[env_var]

    return config


def reload_services() -> None:
    """
    Force-reload the app config and service modules so they pick up
    new environment variable values (e.g. after the user saves settings).

    This re-evaluates module-level globals like ``_HEADERS`` and ``_client``.
    """
    modules_to_reload = [
        "app.config",
        "app.services.github_service",
        "app.services.clickup_service",
        "app.services.slack_service",
        "app.services.slack_activity_service",
        "app.services.ai_summary_service",
        "app.services.summary_service",
        "app.scheduler",
    ]

    for mod_name in modules_to_reload:
        if mod_name in sys.modules:
            try:
                importlib.reload(sys.modules[mod_name])
            except Exception:
                pass  # best-effort reload


def apply_config_and_reload(config: Dict[str, Any]) -> None:
    """
    Convenience: set env vars from config, then reload all service modules.

    Call this when the user saves new settings in the Settings view.
    """
    init_env_from_config(config)
    reload_services()
