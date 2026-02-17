"""
Slack Activity Service — fetches today's discussions from monitored channels.

Uses the Slack Web API ``conversations.history`` and ``conversations.info``
to pull messages posted today from channels the user wants to track.

Required bot token scopes (in addition to existing):
  - channels:history
  - channels:read
  - groups:history   (for private channels)
  - groups:read
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings
from app.logger import get_logger
from app.models.activity_models import SlackChannelActivity, SlackMessage

logger = get_logger(__name__)


def _get_today_range() -> tuple[str, str]:
    """Return (oldest, latest) Unix timestamps for today in user's timezone."""
    try:
        from zoneinfo import ZoneInfo
        tz_name = settings.timezone if settings.timezone else "UTC"
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = timezone.utc
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return str(start.timestamp()), str(now.timestamp())


def _resolve_user_name(client: WebClient, user_id: str) -> str:
    """Best-effort resolve a Slack user ID to display name."""
    try:
        resp = client.users_info(user=user_id)
        profile = resp.get("user", {}).get("profile", {})
        return (
            profile.get("display_name")
            or profile.get("real_name")
            or user_id
        )
    except Exception:
        return user_id


def _resolve_channel_name(client: WebClient, channel_id: str) -> str:
    """Best-effort resolve a channel ID to its name."""
    try:
        resp = client.conversations_info(channel=channel_id)
        return resp.get("channel", {}).get("name", channel_id)
    except Exception:
        return channel_id


def fetch_slack_channel_activity(
    monitor_channels: str = "",
) -> SlackChannelActivity:
    """
    Fetch today's messages from the configured Slack channels.

    Args:
        monitor_channels: Comma-separated channel IDs to monitor.

    Returns:
        SlackChannelActivity with today's messages.
    """
    if not settings or not settings.slack_bot_token:
        return SlackChannelActivity()

    channels_str = monitor_channels.strip()
    if not channels_str:
        return SlackChannelActivity()

    channel_ids = [c.strip() for c in channels_str.split(",") if c.strip()]
    if not channel_ids:
        return SlackChannelActivity()

    client = WebClient(token=settings.slack_bot_token)
    oldest, latest = _get_today_range()

    all_messages: List[SlackMessage] = []
    user_cache: dict[str, str] = {}
    channel_name_cache: dict[str, str] = {}

    for ch_id in channel_ids:
        if ch_id not in channel_name_cache:
            channel_name_cache[ch_id] = _resolve_channel_name(client, ch_id)
        ch_name = channel_name_cache[ch_id]

        try:
            cursor: Optional[str] = None
            while True:
                kwargs = {
                    "channel": ch_id,
                    "oldest": oldest,
                    "latest": latest,
                    "limit": 100,
                    "inclusive": True,
                }
                if cursor:
                    kwargs["cursor"] = cursor

                resp = client.conversations_history(**kwargs)
                messages = resp.get("messages", [])

                for msg in messages:
                    # Skip bot messages and join/leave messages
                    subtype = msg.get("subtype", "")
                    if subtype in ("bot_message", "channel_join", "channel_leave"):
                        continue

                    user_id = msg.get("user", "")
                    if user_id and user_id not in user_cache:
                        user_cache[user_id] = _resolve_user_name(client, user_id)
                    user_name = user_cache.get(user_id, user_id)

                    text = msg.get("text", "").strip()
                    if not text:
                        continue

                    ts_float = float(msg.get("ts", "0"))
                    dt = datetime.fromtimestamp(ts_float, tz=timezone.utc)

                    all_messages.append(SlackMessage(
                        user_id=user_id,
                        user_name=user_name,
                        text=text[:500],
                        channel_id=ch_id,
                        channel_name=ch_name,
                        timestamp=dt,
                        thread_ts=msg.get("thread_ts"),
                    ))

                meta = resp.get("response_metadata", {})
                cursor = meta.get("next_cursor")
                if not cursor:
                    break

            logger.info(
                "Slack channel %s (%s): fetched %d messages",
                ch_name, ch_id, len([m for m in all_messages if m.channel_id == ch_id]),
            )

        except SlackApiError as exc:
            err = exc.response["error"]
            if err == "missing_scope":
                logger.warning(
                    "Slack missing_scope for channel %s — go to api.slack.com/apps > "
                    "your bot > OAuth & Permissions > add scopes: channels:history, "
                    "channels:read, groups:history, groups:read — then reinstall the app",
                    ch_id,
                )
            elif err == "not_in_channel":
                logger.warning(
                    "Bot not in channel %s — invite it with: /invite @YourBotName",
                    ch_id,
                )
            else:
                logger.warning("Slack API error for channel %s: %s", ch_id, err)
        except Exception:
            logger.exception("Error fetching Slack channel %s", ch_id)

    logger.info("Total Slack messages fetched: %d from %d channels", len(all_messages), len(channel_ids))
    return SlackChannelActivity(messages=all_messages)
