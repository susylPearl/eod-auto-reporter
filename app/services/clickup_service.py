"""
ClickUp Service — fetches today's task and comment activity.

Uses the ClickUp API v2.  All date comparisons use UTC millisecond
timestamps which is the native format ClickUp uses internally.

Only tasks that are "in progress" (active work) or "completed/closed"
today are included.  Tasks merely visited or in "Open" status are excluded.
Parent-child (subtask) relationships are preserved via ``parent_id``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import requests

from app.config import settings
from app.logger import get_logger
from app.models.activity_models import (
    ClickUpActivity,
    ClickUpComment,
    ClickUpTask,
)

logger = get_logger(__name__)

_BASE = "https://api.clickup.com/api/v2"
_HEADERS: Dict[str, str] = {
    "Authorization": settings.clickup_api_token,
    "Content-Type": "application/json",
}

# Statuses that mean the task is completed
_COMPLETED_STATUSES: Set[str] = {
    "complete",
    "closed",
    "done",
    "resolved",
}

# Statuses that indicate active work (in progress)
_IN_PROGRESS_STATUSES: Set[str] = {
    "in progress",
    "in review",
    "review",
    "qa",
    "testing",
    "dev-test",
    "ready for review",
    "in development",
}


def _start_of_today_ms() -> int:
    """Return start-of-today UTC as a Unix epoch in milliseconds."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start.timestamp() * 1000)


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _get(url: str, params: Dict[str, Any] | None = None) -> Any:
    resp = requests.get(url, headers=_HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------------
# Tasks
# ------------------------------------------------------------------

def _fetch_tasks(team_id: str, user_id: int) -> List[Dict[str, Any]]:
    """
    Fetch tasks from ClickUp that were updated today by the given user.

    Uses the *filtered team tasks* endpoint which allows filtering by
    assignee and date_updated range.
    """
    start_ms = _start_of_today_ms()
    end_ms = _now_ms()

    url = f"{_BASE}/team/{team_id}/task"
    params: Dict[str, Any] = {
        "assignees[]": user_id,
        "date_updated_gt": start_ms,
        "date_updated_lt": end_ms,
        "subtasks": "true",
        "include_closed": "true",
        "order_by": "updated",
        "reverse": "true",
        "page": 0,
    }

    all_tasks: List[Dict[str, Any]] = []
    while True:
        data = _get(url, params=params)
        tasks = data.get("tasks", [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        if data.get("last_page", True):
            break
        params["page"] += 1  # type: ignore[operator]

    return all_tasks


def _fetch_parent_task(parent_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single parent task by ID (for hierarchy building)."""
    try:
        return _get(f"{_BASE}/task/{parent_id}")
    except requests.HTTPError:
        logger.warning("Could not fetch parent task %s", parent_id)
        return None


def _to_clickup_task(t: Dict[str, Any]) -> ClickUpTask:
    """Convert a raw ClickUp API task dict to a ClickUpTask model."""
    status_label = t.get("status", {}).get("status", "unknown").lower()
    task_url = t.get("url", f"https://app.clickup.com/t/{t['id']}")
    parent_id = t.get("parent") or None

    return ClickUpTask(
        task_id=t["id"],
        name=t.get("name", "Untitled"),
        status=status_label,
        previous_status=None,
        parent_id=parent_id,
        url=task_url,
        date_updated=datetime.fromtimestamp(
            int(t.get("date_updated", 0)) / 1000, tz=timezone.utc
        ),
    )


def _parse_tasks(raw_tasks: List[Dict[str, Any]]) -> tuple[
    List[ClickUpTask], List[ClickUpTask], List[ClickUpTask], Dict[str, ClickUpTask]
]:
    """
    Classify raw task dicts into:
      - tasks_in_progress  (status is "in progress", "review", etc.)
      - tasks_completed    (status is "closed" / "done" / "complete")
      - all_active         (union of above for building hierarchy)
      - parent_tasks       (parent tasks fetched for hierarchy, keyed by ID)

    Tasks in "Open", "to do", "backlog" etc. are excluded.
    """
    tasks_in_progress: List[ClickUpTask] = []
    tasks_completed: List[ClickUpTask] = []
    all_active: List[ClickUpTask] = []
    parent_ids_needed: Set[str] = set()

    for t in raw_tasks:
        status_label = t.get("status", {}).get("status", "unknown").lower()

        # Only include completed or in-progress tasks
        if status_label in _COMPLETED_STATUSES:
            task = _to_clickup_task(t)
            tasks_completed.append(task)
            all_active.append(task)
        elif status_label in _IN_PROGRESS_STATUSES:
            task = _to_clickup_task(t)
            tasks_in_progress.append(task)
            all_active.append(task)
        else:
            logger.debug(
                "Skipping task '%s' — status '%s'",
                t.get("name", "?"),
                status_label,
            )
            continue

        # Track parent IDs we need to fetch for hierarchy
        parent_id = t.get("parent")
        if parent_id:
            parent_ids_needed.add(parent_id)

    # Fetch parent tasks that aren't already in our active list
    active_ids = {t.task_id for t in all_active}
    parent_tasks: Dict[str, ClickUpTask] = {}
    for pid in parent_ids_needed:
        if pid not in active_ids:
            raw = _fetch_parent_task(pid)
            if raw:
                parent_tasks[pid] = _to_clickup_task(raw)

    return tasks_in_progress, tasks_completed, all_active, parent_tasks


# ------------------------------------------------------------------
# Comments
# ------------------------------------------------------------------

def _fetch_recent_comments(task_ids: List[str], user_id: int) -> List[ClickUpComment]:
    """
    For each task, pull comments and keep those authored by *user_id* today.

    To avoid excessive API calls we limit to the first 20 tasks.
    """
    start_ms = _start_of_today_ms()
    comments: List[ClickUpComment] = []

    for tid in task_ids[:20]:
        try:
            data = _get(f"{_BASE}/task/{tid}/comment")
            for c in data.get("comments", []):
                comment_user = c.get("user", {}).get("id", 0)
                comment_date_ms = int(c.get("date", 0))
                if comment_user == user_id and comment_date_ms >= start_ms:
                    text_parts = []
                    for part in c.get("comment", []):
                        text_parts.append(part.get("text", ""))
                    plain_text = " ".join(text_parts).strip()[:200]

                    comments.append(
                        ClickUpComment(
                            task_id=tid,
                            task_name=c.get("task", {}).get("name", tid),
                            comment_text=plain_text or "(empty comment)",
                            date=datetime.fromtimestamp(
                                comment_date_ms / 1000, tz=timezone.utc
                            ),
                        )
                    )
        except requests.HTTPError:
            logger.warning("Could not fetch comments for task %s", tid)

    return comments


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def fetch_clickup_activity() -> ClickUpActivity:
    """
    Fetch today's ClickUp activity for the configured user.

    Only returns:
      - Tasks completed/closed today
      - Tasks in progress (active work)

    Parent-child relationships are preserved via ``parent_id``.
    Visited/open tasks are excluded.
    """
    team_id = settings.clickup_team_id
    user_id = settings.clickup_user_id
    logger.info("Fetching ClickUp activity for team=%s user=%s", team_id, user_id)

    try:
        raw_tasks = _fetch_tasks(team_id, user_id)
        logger.info("ClickUp raw tasks fetched: %d", len(raw_tasks))

        tasks_in_progress, tasks_completed, all_active, parent_tasks = _parse_tasks(raw_tasks)

        # Include parent tasks in the updated list for hierarchy building
        all_for_hierarchy = list(all_active)
        for pt in parent_tasks.values():
            all_for_hierarchy.append(pt)

        task_ids = [t.task_id for t in all_active]
        comments = _fetch_recent_comments(task_ids, user_id)

        activity = ClickUpActivity(
            tasks_updated=all_for_hierarchy,
            tasks_completed=tasks_completed,
            status_changes=tasks_in_progress,
            comments=comments,
        )

        logger.info(
            "ClickUp activity (filtered): %d in-progress, %d completed, %d total with parents",
            len(tasks_in_progress),
            len(tasks_completed),
            len(all_for_hierarchy),
        )
        return activity

    except Exception:
        logger.exception("Failed to fetch ClickUp activity")
        return ClickUpActivity()
