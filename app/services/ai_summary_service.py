"""
AI Summary Service — generates a brief summary of all daily activity.

Uses OpenAI-compatible APIs (OpenAI, Azure OpenAI, or any provider
that supports the chat completions endpoint).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.logger import get_logger
from app.models.activity_models import (
    AISummary,
    ClickUpActivity,
    GitHubActivity,
    SlackChannelActivity,
)

logger = get_logger(__name__)


def _build_activity_text(
    gh: Optional[GitHubActivity],
    cu: Optional[ClickUpActivity],
    slack: Optional[SlackChannelActivity],
) -> str:
    """Flatten all activity into a plain-text digest for the AI prompt."""
    parts: list[str] = []

    if gh:
        if gh.commits:
            parts.append(f"GitHub Commits ({len(gh.commits)}):")
            for c in gh.commits[:15]:
                repo_short = c.repo.split("/")[-1]
                parts.append(f"  - [{repo_short}] {c.message}")
        if gh.prs_opened:
            parts.append(f"PRs Opened ({len(gh.prs_opened)}):")
            for pr in gh.prs_opened[:10]:
                parts.append(f"  - [{pr.repo.split('/')[-1]}] {pr.title}")
        if gh.prs_merged:
            parts.append(f"PRs Merged ({len(gh.prs_merged)}):")
            for pr in gh.prs_merged[:10]:
                parts.append(f"  - [{pr.repo.split('/')[-1]}] {pr.title}")

    if cu:
        if cu.tasks_completed:
            parts.append(f"Tasks Completed ({len(cu.tasks_completed)}):")
            for t in cu.tasks_completed[:10]:
                parts.append(f"  - {t.name} [{t.status}]")
        if cu.status_changes:
            parts.append(f"Tasks In Progress ({len(cu.status_changes)}):")
            for t in cu.status_changes[:10]:
                parts.append(f"  - {t.name} [{t.status}]")
        if cu.comments:
            parts.append(f"ClickUp Comments ({len(cu.comments)}):")
            for c in cu.comments[:5]:
                parts.append(f"  - On '{c.task_name}': {c.comment_text[:100]}")

    if slack and slack.messages:
        parts.append(f"Slack Discussions ({len(slack.messages)} messages):")
        # Group by channel
        by_channel: dict[str, list[str]] = {}
        for m in slack.messages[:30]:
            key = m.channel_name or m.channel_id
            by_channel.setdefault(key, []).append(
                f"  [{m.user_name}]: {m.text[:150]}"
            )
        for ch_name, msgs in by_channel.items():
            parts.append(f"  #{ch_name}:")
            parts.extend(msgs[:15])

    return "\n".join(parts) if parts else "No activity recorded today."


_SYSTEM_PROMPT = (
    "You are an expert engineering manager writing a brief end-of-day summary. "
    "Summarize the developer's daily activity into 3-5 concise bullet points. "
    "Focus on what was accomplished, what's in progress, and key discussions. "
    "Be professional and brief. Use plain text, no markdown formatting."
)


def generate_ai_summary(
    gh: Optional[GitHubActivity] = None,
    cu: Optional[ClickUpActivity] = None,
    slack: Optional[SlackChannelActivity] = None,
    api_key: str = "",
    model: str = "gemini-2.0-flash",
    base_url: str = "",
) -> Optional[AISummary]:
    """
    Generate an AI summary of today's activity.

    Uses the OpenAI-compatible chat completions API. Works with any provider
    that supports this endpoint (OpenAI, Google Gemini, Groq, Ollama, etc.).

    Args:
        gh: GitHub activity data.
        cu: ClickUp activity data.
        slack: Slack channel discussions.
        api_key: API key for the provider.
        model: Model name (e.g. gemini-2.0-flash, llama-3.3-70b-versatile).
        base_url: Custom API base URL. Empty string uses OpenAI default.

    Returns:
        AISummary or None if generation fails or no API key.
    """
    if not api_key:
        logger.debug("No AI API key configured — skipping summary generation")
        return None

    activity_text = _build_activity_text(gh, cu, slack)
    if activity_text == "No activity recorded today.":
        return AISummary(
            summary_text="No activity recorded today.",
            generated_at=datetime.now(timezone.utc),
        )

    try:
        from openai import OpenAI

        client_kwargs: dict = {"api_key": api_key}
        if base_url and base_url.strip():
            client_kwargs["base_url"] = base_url.strip()

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Here is today's developer activity:\n\n{activity_text}\n\n"
                        "Please provide a brief 3-5 bullet point summary."
                    ),
                },
            ],
            max_tokens=400,
            temperature=0.3,
        )
        summary_text = response.choices[0].message.content or ""
        logger.info("AI summary generated (%d chars) via %s", len(summary_text), model)

        return AISummary(
            summary_text=summary_text.strip(),
            generated_at=datetime.now(timezone.utc),
        )

    except ImportError:
        logger.warning("openai package not installed — pip install openai")
        return AISummary(
            summary_text="(AI summary unavailable — install 'openai' package)",
            generated_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.error("AI summary generation failed: %s", exc)
        return AISummary(
            summary_text=f"(AI summary error: {str(exc)[:100]})",
            generated_at=datetime.now(timezone.utc),
        )
