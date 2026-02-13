"""
GitHub Service — fetches today's commits and pull-request activity.

Uses the GitHub REST API v3 with a Personal Access Token (classic or
fine-grained). All timestamps are compared in UTC so the service works
consistently regardless of the server's local timezone.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import requests

from app.config import settings
from app.logger import get_logger
from app.models.activity_models import (
    GitHubActivity,
    GitHubCommit,
    GitHubPR,
)

logger = get_logger(__name__)

_BASE = "https://api.github.com"
_HEADERS: Dict[str, str] = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _start_of_today_utc() -> datetime:
    """Return midnight UTC for the current day."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _get(url: str, params: Dict[str, Any] | None = None) -> Any:
    """Thin wrapper around requests.get with error handling."""
    resp = requests.get(url, headers=_HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# Commits
# ------------------------------------------------------------------

def _fetch_today_events(username: str) -> List[Dict[str, Any]]:
    """
    Fetch public events for *username* and return only PushEvents
    that happened today (UTC).

    GitHub's /users/{user}/events endpoint returns up to 300 events
    (paginated, 30 per page, max 10 pages).  We stop early once we
    hit events older than today.
    """
    start = _start_of_today_utc()
    push_events: List[Dict[str, Any]] = []

    for page in range(1, 11):
        url = f"{_BASE}/users/{username}/events"
        events = _get(url, params={"per_page": 100, "page": page})
        if not events:
            break

        for event in events:
            created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
            if created < start:
                return push_events  # older than today → stop
            if event["type"] == "PushEvent":
                push_events.append(event)

    return push_events


def _parse_commits(push_events: List[Dict[str, Any]], username: str) -> List[GitHubCommit]:
    """Extract individual commits from PushEvent payloads."""
    commits: List[GitHubCommit] = []
    seen_shas: set[str] = set()

    for event in push_events:
        repo_name = event["repo"]["name"]
        for c in event.get("payload", {}).get("commits", []):
            sha = c["sha"]
            if sha in seen_shas:
                continue
            seen_shas.add(sha)

            # Only include commits where the author matches the tracked user
            # (PushEvents can contain co-authored commits)
            author_email = c.get("author", {}).get("email", "")
            author_name = c.get("author", {}).get("name", "")
            if username.lower() not in author_name.lower() and username.lower() not in author_email.lower():
                # Fallback: still include, but try matching via distinct flag
                if not c.get("distinct", True):
                    continue

            commits.append(
                GitHubCommit(
                    sha=sha,
                    message=c["message"].split("\n")[0][:120],
                    repo=repo_name,
                    url=f"https://github.com/{repo_name}/commit/{sha}",
                    timestamp=datetime.fromisoformat(
                        event["created_at"].replace("Z", "+00:00")
                    ),
                )
            )

    return commits


# ------------------------------------------------------------------
# Pull Requests
# ------------------------------------------------------------------

def _fetch_prs(username: str) -> tuple[List[GitHubPR], List[GitHubPR]]:
    """
    Use the search API to find PRs authored by *username* that were
    created or merged today.

    Returns:
        (prs_opened_today, prs_merged_today)
    """
    start = _start_of_today_utc()
    today_str = start.strftime("%Y-%m-%d")

    opened: List[GitHubPR] = []
    merged: List[GitHubPR] = []

    # --- PRs created today ---
    query_opened = f"author:{username} type:pr created:>={today_str}"
    try:
        data = _get(
            f"{_BASE}/search/issues",
            params={"q": query_opened, "per_page": 50, "sort": "created", "order": "desc"},
        )
        for item in data.get("items", []):
            repo_full = item["repository_url"].replace("https://api.github.com/repos/", "")
            opened.append(
                GitHubPR(
                    number=item["number"],
                    title=item["title"],
                    repo=repo_full,
                    state=item["state"],
                    url=item["html_url"],
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    merged_at=None,
                )
            )
    except requests.HTTPError as exc:
        logger.warning("GitHub search (opened PRs) failed: %s", exc)

    # --- PRs merged today ---
    query_merged = f"author:{username} type:pr merged:>={today_str}"
    try:
        data = _get(
            f"{_BASE}/search/issues",
            params={"q": query_merged, "per_page": 50, "sort": "updated", "order": "desc"},
        )
        for item in data.get("items", []):
            repo_full = item["repository_url"].replace("https://api.github.com/repos/", "")
            pr_obj = GitHubPR(
                number=item["number"],
                title=item["title"],
                repo=repo_full,
                state="merged",
                url=item["html_url"],
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                merged_at=None,  # search/issues doesn't return merged_at directly
            )
            merged.append(pr_obj)
    except requests.HTTPError as exc:
        logger.warning("GitHub search (merged PRs) failed: %s", exc)

    return opened, merged


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def fetch_github_activity() -> GitHubActivity:
    """
    Fetch all of today's GitHub activity for the configured user.

    Returns a ``GitHubActivity`` model that the summary service consumes.
    """
    username = settings.github_username
    logger.info("Fetching GitHub activity for user=%s", username)

    try:
        push_events = _fetch_today_events(username)
        commits = _parse_commits(push_events, username)
        prs_opened, prs_merged = _fetch_prs(username)

        activity = GitHubActivity(
            commits=commits,
            prs_opened=prs_opened,
            prs_merged=prs_merged,
        )

        logger.info(
            "GitHub activity collected: %d commits, %d PRs opened, %d PRs merged",
            len(activity.commits),
            len(activity.prs_opened),
            len(activity.prs_merged),
        )
        return activity

    except Exception:
        logger.exception("Failed to fetch GitHub activity")
        return GitHubActivity()
