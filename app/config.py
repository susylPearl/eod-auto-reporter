"""
Application configuration using Pydantic BaseSettings.

All configuration is loaded from environment variables (or a .env file).
Provides typed, validated access to tokens, IDs, and scheduling parameters.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the EOD Auto Reporter."""

    # --- GitHub ---
    github_token: str = Field(..., description="GitHub personal access token")
    github_username: str = Field(..., description="GitHub username to track activity for")

    # --- ClickUp ---
    clickup_api_token: str = Field(..., description="ClickUp API v2 personal token")
    clickup_team_id: str = Field(..., description="ClickUp workspace (team) ID")
    clickup_user_id: int = Field(..., description="Numeric ClickUp user ID for the authenticated user")

    # --- Slack ---
    slack_bot_token: str = Field(..., description="Slack Bot User OAuth Token (xoxb-...)")
    slack_channel: str = Field(..., description="Slack channel ID or name to post the EOD report")
    slack_user_id: str = Field(default="", description="Your Slack user ID (for OOO check & profile picture)")
    slack_display_name: str = Field(default="", description="Display name shown on EOD posts (e.g. Chiranjhivi Ghimire)")
    slack_icon_url: str = Field(default="", description="URL to your profile picture for EOD posts")

    # --- Scheduler ---
    report_hour: int = Field(default=18, ge=0, le=23, description="Hour (24h) to send the daily report")
    report_minute: int = Field(default=0, ge=0, le=59, description="Minute to send the daily report")
    timezone: str = Field(default="Asia/Kolkata", description="IANA timezone for the scheduler")

    # --- App ---
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    app_env: str = Field(default="production", description="Running environment (development, production)")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Singleton — import this everywhere
settings = Settings()
