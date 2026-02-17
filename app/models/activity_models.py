"""
Domain models for GitHub and ClickUp activity.

These Pydantic models define the structured data that flows between
services. They are intentionally decoupled from API response shapes so
the system is resilient to upstream schema changes.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

class GitHubCommit(BaseModel):
    """A single commit authored by the tracked user."""

    sha: str = Field(..., description="Full commit SHA")
    message: str = Field(..., description="First line of the commit message")
    repo: str = Field(..., description="Repository full name (owner/repo)")
    url: str = Field(..., description="HTML URL to the commit on GitHub")
    timestamp: datetime = Field(..., description="Authoring timestamp (ISO-8601)")


class GitHubPR(BaseModel):
    """A pull request opened or merged by the tracked user."""

    number: int = Field(..., description="PR number within the repo")
    title: str = Field(..., description="PR title")
    repo: str = Field(..., description="Repository full name (owner/repo)")
    state: str = Field(..., description="open | closed | merged")
    url: str = Field(..., description="HTML URL to the PR")
    created_at: datetime
    merged_at: Optional[datetime] = None


class GitHubActivity(BaseModel):
    """Aggregated GitHub activity for a single day."""

    commits: List[GitHubCommit] = Field(default_factory=list)
    prs_opened: List[GitHubPR] = Field(default_factory=list)
    prs_merged: List[GitHubPR] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# ClickUp
# ---------------------------------------------------------------------------

class ClickUpTask(BaseModel):
    """A ClickUp task that was touched today."""

    task_id: str = Field(..., description="ClickUp task ID")
    name: str = Field(..., description="Task name / title")
    status: str = Field(..., description="Current status label")
    previous_status: Optional[str] = Field(None, description="Status before last transition")
    parent_id: Optional[str] = Field(None, description="Parent task ID (None if top-level)")
    url: str = Field(..., description="URL to the task in ClickUp")
    date_updated: datetime


class ClickUpComment(BaseModel):
    """A comment the user posted on a ClickUp task today."""

    task_id: str
    task_name: str
    comment_text: str = Field(..., description="Plain-text comment body (truncated to 200 chars)")
    date: datetime


class ClickUpActivity(BaseModel):
    """Aggregated ClickUp activity for a single day."""

    tasks_updated: List[ClickUpTask] = Field(default_factory=list)
    tasks_completed: List[ClickUpTask] = Field(default_factory=list)
    status_changes: List[ClickUpTask] = Field(default_factory=list)
    comments: List[ClickUpComment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Slack Channel Activity
# ---------------------------------------------------------------------------

class SlackMessage(BaseModel):
    """A single Slack message from a monitored channel."""

    user_id: str = Field("", description="Slack user ID of the sender")
    user_name: str = Field("", description="Display name of the sender")
    text: str = Field("", description="Message text content")
    channel_id: str = Field("", description="Channel ID")
    channel_name: str = Field("", description="Channel name")
    timestamp: datetime = Field(default_factory=datetime.now)
    thread_ts: Optional[str] = Field(None, description="Thread parent timestamp (if threaded)")


class SlackChannelActivity(BaseModel):
    """Activity from monitored Slack channels for a single day."""

    messages: List[SlackMessage] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AI Summary
# ---------------------------------------------------------------------------

class AISummary(BaseModel):
    """AI-generated summary of all daily activity."""

    summary_text: str = Field("", description="Brief AI-generated summary")
    generated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Unified
# ---------------------------------------------------------------------------

class DailyActivity(BaseModel):
    """Combined activity payload handed to the summary generator."""

    date: str = Field(..., description="ISO date string (YYYY-MM-DD)")
    github: GitHubActivity = Field(default_factory=GitHubActivity)
    clickup: ClickUpActivity = Field(default_factory=ClickUpActivity)
    slack_discussions: SlackChannelActivity = Field(default_factory=SlackChannelActivity)
    manual_updates: List[str] = Field(default_factory=list)
    ai_summary: Optional[AISummary] = None
