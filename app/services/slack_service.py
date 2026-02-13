"""
Slack Service — posts messages and checks user status.

Uses the ``slack_sdk`` WebClient for all Slack Web API interactions.
The bot's display name and profile picture are configured directly
in the Slack App settings (Basic Information → Display Information).

Required bot token scopes:
  - chat:write
  - users.profile:read   (to check OOO status)
  - users:read            (to look up user info)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

_client = WebClient(token=settings.slack_bot_token)

# Cached user identity (fetched once per process)
_cached_identity: Optional[tuple[str, str]] = None  # (username, icon_url)


def _resolve_identity() -> tuple[Optional[str], Optional[str]]:
    """
    Resolve the user's real name and profile picture URL.

    Returns:
        (username, icon_url) — either may be None.
    """
    global _cached_identity
    if _cached_identity is not None:
        name, icon = _cached_identity
        return name or None, icon or None

    if not settings.slack_user_id:
        _cached_identity = ("", "")
        return None, None

    try:
        resp = _client.users_info(user=settings.slack_user_id)
        profile = resp.get("user", {}).get("profile", {})
        name = profile.get("real_name") or profile.get("display_name", "")
        icon = profile.get("image_192") or profile.get("image_72") or ""
        _cached_identity = (name, icon)
        logger.info("Resolved Slack identity: name=%r icon=%s", name, icon[:50] + "..." if len(icon) > 50 else icon)
        return name or None, icon or None
    except Exception:
        logger.debug("Could not fetch user profile for identity override")
        _cached_identity = ("", "")
        return None, None


def send_message(channel: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> bool:
    """
    Post a message to the given Slack channel.

    Args:
        channel: Channel ID or name.
        text:    Plain-text fallback (shown in notifications).
        blocks:  Optional Block Kit blocks for rich formatting.

    Returns:
        ``True`` if the message was sent successfully.
    """
    try:
        kwargs: dict = {
            "channel": channel,
            "text": text,
            "unfurl_links": False,
            "unfurl_media": False,
        }

        if blocks:
            kwargs["blocks"] = blocks

        username, icon_url = _resolve_identity()
        if username:
            kwargs["username"] = username
        if icon_url:
            kwargs["icon_url"] = icon_url

        response = _client.chat_postMessage(**kwargs)
        logger.info(
            "Slack message sent to %s as %r (ts=%s)",
            channel,
            username or "(bot default)",
            response.get("ts"),
        )
        return True

    except SlackApiError as exc:
        logger.error(
            "Slack API error (channel=%s): %s — %s",
            channel,
            exc.response["error"],
            exc.response.get("response_metadata", {}).get("messages", ""),
        )
        return False

    except Exception:
        logger.exception("Unexpected error sending Slack message to %s", channel)
        return False


def is_user_ooo(user_id: Optional[str] = None) -> bool:
    """
    Check whether the Slack user's status indicates OOO.

    Uses SLACK_USER_ID from config if no user_id is passed.

    Args:
        user_id: Slack user ID.  If ``None``, uses config or bot identity.

    Returns:
        ``True`` if the user appears to be out-of-office.
    """
    try:
        if user_id is None:
            user_id = settings.slack_user_id or None

        if user_id is None:
            auth = _client.auth_test()
            user_id = auth["user_id"]

        profile_resp = _client.users_profile_get(user=user_id)
        profile = profile_resp.get("profile", {})

        status_text: str = (profile.get("status_text") or "").lower()
        status_emoji: str = profile.get("status_emoji") or ""

        ooo_keywords = {"ooo", "out of office", "vacation", "pto", "on leave", "away"}
        ooo_emojis = {":palm_tree:", ":no_entry:", ":airplane:", ":beach_with_umbrella:"}

        if any(kw in status_text for kw in ooo_keywords):
            logger.info("User %s is OOO (status_text=%r)", user_id, status_text)
            return True

        if status_emoji in ooo_emojis:
            logger.info("User %s is OOO (status_emoji=%s)", user_id, status_emoji)
            return True

        return False

    except SlackApiError as exc:
        logger.warning("Could not check OOO status: %s", exc.response["error"])
        return False

    except Exception:
        logger.exception("Unexpected error checking OOO status")
        return False
