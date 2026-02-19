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

_SLACK_SUMMARY_PROMPT = (
    "You are a concise technical writer. Summarize the Slack channel discussions below "
    "into brief, actionable bullet points per channel. "
    "Focus on: key decisions, blockers raised, action items, and important updates. "
    "Skip greetings, small talk, and emoji reactions. "
    "Use plain text, no markdown. Keep each bullet to one line."
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


# ------------------------------------------------------------------
# Slack channel summarization
# ------------------------------------------------------------------

def _build_slack_digest(slack: SlackChannelActivity) -> dict[str, str]:
    """Group Slack messages by channel and return per-channel plain text."""
    by_channel: dict[str, list[str]] = {}
    for m in slack.messages:
        key = m.channel_name or m.channel_id
        by_channel.setdefault(key, []).append(
            f"[{m.user_name}]: {m.text[:200]}"
        )
    return {ch: "\n".join(msgs[:40]) for ch, msgs in by_channel.items()}


def summarize_slack_channels(
    slack: Optional[SlackChannelActivity],
    api_key: str = "",
    model: str = "gemini-2.0-flash",
    base_url: str = "",
) -> dict[str, str]:
    """
    Summarize Slack channel discussions using AI.

    Returns a dict mapping channel name to a brief summary string.
    Returns empty dict if no messages, no API key, or on error.
    """
    if not slack or not slack.messages:
        return {}
    if not api_key:
        return {}

    digests = _build_slack_digest(slack)
    if not digests:
        return {}

    prompt_parts = []
    for ch_name, text in digests.items():
        prompt_parts.append(f"=== #{ch_name} ===\n{text}")
    full_prompt = "\n\n".join(prompt_parts)

    try:
        from openai import OpenAI

        client_kwargs: dict = {"api_key": api_key}
        if base_url and base_url.strip():
            client_kwargs["base_url"] = base_url.strip().rstrip("/")

        logger.info("Slack summarization: model=%s, channels=%d", model, len(digests))
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SLACK_SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Summarize each channel's discussions into 2-4 bullet points:\n\n"
                        f"{full_prompt}"
                    ),
                },
            ],
            max_tokens=600,
            temperature=0.2,
        )
        raw = (response.choices[0].message.content or "").strip()
        logger.info("Slack channel summaries generated (%d chars) via %s", len(raw), model)

        return _parse_channel_summaries(raw, list(digests.keys()))

    except ImportError:
        logger.warning("openai package not installed — cannot summarize Slack")
        return {}
    except Exception as exc:
        logger.exception("Slack channel summarization failed: %s", exc)
        return {}


def _parse_channel_summaries(raw: str, channel_names: list[str]) -> dict[str, str]:
    """
    Parse the AI response into per-channel summaries.

    Handles two formats:
      1. Structured: "#channel-name" header followed by bullets
      2. Flat: all bullets lumped together (assign to first channel)
    """
    result: dict[str, str] = {}
    current_channel: Optional[str] = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        matched_channel = None
        for name in channel_names:
            if name.lower() in stripped.lower() and (
                stripped.startswith("#") or stripped.startswith("===")
            ):
                matched_channel = name
                break

        if matched_channel:
            if current_channel and current_lines:
                result[current_channel] = "\n".join(current_lines)
            current_channel = matched_channel
            current_lines = []
        else:
            clean = stripped.lstrip("-•*").strip()
            if clean:
                current_lines.append(f"• {clean}")

    if current_channel and current_lines:
        result[current_channel] = "\n".join(current_lines)

    if not result and current_lines:
        fallback = channel_names[0] if channel_names else "general"
        result[fallback] = "\n".join(current_lines)

    return result
