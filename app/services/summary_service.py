"""
Summary Service — transforms raw activity into Slack Block Kit rich_text.

Uses Slack's native ``rich_text_list`` blocks with ``indent`` levels
so bullets are rendered at the correct size by Slack itself:

    indent 0  →  •  (filled circle)
    indent 1  →  ○  (open circle)
    indent 2  →  ■  (small square)

This matches the exact styling Slack's own rich-text editor produces.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from app.logger import get_logger
from app.models.activity_models import ClickUpActivity, ClickUpComment, ClickUpTask, DailyActivity, GitHubActivity

logger = get_logger(__name__)

_MAX_ITEMS = 15


def _status_prefix(status: str) -> str:
    """Map a ClickUp status to a human-friendly prefix."""
    mapping = {
        "in progress": "wip",
        "in review": "dev-test",
        "review": "dev-test",
        "qa": "dev-test",
        "testing": "dev-test",
        "done": "completed",
        "complete": "completed",
        "closed": "completed",
        "resolved": "completed",
    }
    return mapping.get(status.lower(), "")


# ------------------------------------------------------------------
# Block Kit helpers
# ------------------------------------------------------------------

def _text(t: str, bold: bool = False, italic: bool = False) -> Dict[str, Any]:
    """Create a rich_text text element."""
    elem: Dict[str, Any] = {"type": "text", "text": t}
    style: Dict[str, bool] = {}
    if bold:
        style["bold"] = True
    if italic:
        style["italic"] = True
    if style:
        elem["style"] = style
    return elem


def _link(url: str, t: str, bold: bool = False) -> Dict[str, Any]:
    """Create a rich_text link element."""
    elem: Dict[str, Any] = {"type": "link", "url": url, "text": t}
    if bold:
        elem["style"] = {"bold": True}
    return elem


def _section(*elements: Dict[str, Any]) -> Dict[str, Any]:
    """Create a rich_text_section."""
    cleaned: List[Dict[str, Any]] = []
    for elem in elements:
        if not elem:
            continue
        # Slack rejects empty rich_text text nodes (must be > 0 chars).
        if elem.get("type") == "text" and not str(elem.get("text", "")):
            continue
        cleaned.append(elem)

    if not cleaned:
        cleaned = [_text(" ")]

    return {"type": "rich_text_section", "elements": cleaned}


def _list_block(indent: int, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create a rich_text_list block.

    Args:
        indent: 0 = top bullet (•), 1 = sub-bullet (○), 2 = sub-sub (■)
        items: List of rich_text_section dicts (one per bullet point).
    """
    return {
        "type": "rich_text_list",
        "style": "bullet",
        "indent": indent,
        "elements": items,
    }


# ------------------------------------------------------------------
# Section builders
# ------------------------------------------------------------------

def _build_github_elements(gh: GitHubActivity) -> List[Dict[str, Any]]:
    """Build Block Kit elements for GitHub activity."""
    elements: List[Dict[str, Any]] = []

    if not gh.commits and not gh.prs_opened and not gh.prs_merged:
        return elements

    # Group by repo
    commits_by_repo: defaultdict[str, list] = defaultdict(list)
    for c in gh.commits[:_MAX_ITEMS]:
        repo_short = c.repo.split("/")[-1]
        commits_by_repo[repo_short].append(c)

    prs_by_repo: defaultdict[str, list] = defaultdict(list)
    for pr in gh.prs_opened[:_MAX_ITEMS]:
        repo_short = pr.repo.split("/")[-1]
        prs_by_repo[repo_short].append(("opened", pr))
    for pr in gh.prs_merged[:_MAX_ITEMS]:
        repo_short = pr.repo.split("/")[-1]
        prs_by_repo[repo_short].append(("merged", pr))

    all_repos = sorted(set(list(commits_by_repo.keys()) + list(prs_by_repo.keys())))

    if len(all_repos) > 1:
        for repo in all_repos:
            # Repo name as indent-1 bullet
            elements.append(_list_block(1, [_section(_text(f"{repo}:"))]))

            # Commits + PRs as indent-2 bullets
            sub_items: List[Dict[str, Any]] = []
            for c in commits_by_repo.get(repo, []):
                sub_items.append(_section(_text(c.message)))
            for action, pr in prs_by_repo.get(repo, []):
                label = "PR merged: " if action == "merged" else "PR opened: "
                sub_items.append(_section(_text(label), _link(pr.url, pr.title)))
            if sub_items:
                elements.append(_list_block(2, sub_items))
    else:
        # Single repo — flat list at indent 1
        sub_items = []
        repo = all_repos[0] if all_repos else ""
        for c in commits_by_repo.get(repo, []):
            sub_items.append(_section(_text(c.message)))
        for action, pr in prs_by_repo.get(repo, []):
            label = "PR merged: " if action == "merged" else "PR opened: "
            sub_items.append(_section(_text(label), _link(pr.url, pr.title)))
        if sub_items:
            elements.append(_list_block(1, sub_items))

    return elements


def _build_task_hierarchy(
    tasks: List[ClickUpTask],
) -> tuple[List[ClickUpTask], Dict[str, List[ClickUpTask]]]:
    """Organize tasks into parent → children groups."""
    task_by_id: Dict[str, ClickUpTask] = {t.task_id: t for t in tasks}
    children: Dict[str, List[ClickUpTask]] = defaultdict(list)
    top_level: List[ClickUpTask] = []

    for t in tasks:
        if t.parent_id and t.parent_id in task_by_id:
            children[t.parent_id].append(t)
        elif t.parent_id is None:
            top_level.append(t)
        else:
            top_level.append(t)

    return top_level, dict(children)


def _group_comments_by_task(comments: List[ClickUpComment]) -> Dict[str, List[str]]:
    """Group comment text snippets by task ID (preserving order)."""
    grouped: Dict[str, List[str]] = defaultdict(list)
    for c in comments:
        text = (c.comment_text or "").strip()
        if text:
            grouped[c.task_id].append(text)
    return grouped


def _shorten_line(text: str, limit: int = 100) -> str:
    """Keep a single line concise for Slack subtext."""
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _task_comment_subtext(task_id: str, comments_by_task: Dict[str, List[str]]) -> str:
    """
    Build a compact 1-2 line comment summary for a task.

    Returned string is meant to be appended as subtext under the task line.
    """
    items = comments_by_task.get(task_id, [])
    if not items:
        return ""

    line1 = f"\nnote: {_shorten_line(items[0])}"
    if len(items) == 1:
        return line1

    line2 = f"\nnote: {_shorten_line(items[1])}"
    return line1 + line2


def _build_clickup_elements(cu: ClickUpActivity) -> List[Dict[str, Any]]:
    """Build Block Kit elements for ClickUp task updates with hierarchy."""
    elements: List[Dict[str, Any]] = []

    if not cu.tasks_updated and not cu.tasks_completed and not cu.comments:
        return elements

    all_tasks = cu.tasks_updated
    top_level, children = _build_task_hierarchy(all_tasks)
    comments_by_task = _group_comments_by_task(cu.comments)

    rendered: set[str] = set()
    completed_ids = {t.task_id for t in cu.tasks_completed}

    # --- Completed tasks first ---
    for t in top_level:
        if t.task_id in completed_ids and t.task_id not in rendered:
            parent_subtext = _task_comment_subtext(t.task_id, comments_by_task)
            parent_items = [_section(_text("completed: "), _link(t.url, t.name), _text(parent_subtext, italic=True))]
            elements.append(_list_block(1, parent_items))
            rendered.add(t.task_id)

            child_items = []
            for child in children.get(t.task_id, []):
                if child.task_id not in rendered:
                    prefix = _status_prefix(child.status)
                    suffix = f" - {prefix}" if prefix else ""
                    child_subtext = _task_comment_subtext(child.task_id, comments_by_task)
                    child_items.append(_section(_link(child.url, child.name), _text(suffix), _text(child_subtext, italic=True)))
                    rendered.add(child.task_id)
            if child_items:
                elements.append(_list_block(2, child_items))

    # Completed subtasks whose parent isn't completed
    for t in cu.tasks_completed:
        if t.task_id not in rendered:
            task_subtext = _task_comment_subtext(t.task_id, comments_by_task)
            elements.append(_list_block(1, [_section(_text("completed: "), _link(t.url, t.name), _text(task_subtext, italic=True))]))
            rendered.add(t.task_id)

    # --- In-progress tasks (parent → subtasks) ---
    for t in top_level:
        if t.task_id in rendered:
            continue
        prefix = _status_prefix(t.status)
        label = f"{prefix}: " if prefix else ""
        parent_subtext = _task_comment_subtext(t.task_id, comments_by_task)
        parent_items = [_section(_text(label), _link(t.url, t.name), _text(parent_subtext, italic=True))]
        elements.append(_list_block(1, parent_items))
        rendered.add(t.task_id)

        child_items = []
        for child in children.get(t.task_id, []):
            if child.task_id not in rendered:
                child_prefix = _status_prefix(child.status)
                suffix = f" - {child_prefix}" if child_prefix else ""
                child_subtext = _task_comment_subtext(child.task_id, comments_by_task)
                child_items.append(_section(_link(child.url, child.name), _text(suffix), _text(child_subtext, italic=True)))
                rendered.add(child.task_id)
        if child_items:
            elements.append(_list_block(2, child_items))

    # Remaining
    remaining_items = []
    for t in all_tasks:
        if t.task_id not in rendered:
            prefix = _status_prefix(t.status)
            label = f"{prefix}: " if prefix else ""
            rem_subtext = _task_comment_subtext(t.task_id, comments_by_task)
            remaining_items.append(_section(_text(label), _link(t.url, t.name), _text(rem_subtext, italic=True)))
            rendered.add(t.task_id)
    if remaining_items:
        elements.append(_list_block(1, remaining_items))

    return elements


def _build_next_elements(activity: DailyActivity) -> List[Dict[str, Any]]:
    """Build 'Next:' items as indent-0 bullets."""
    completed_ids = {t.task_id for t in activity.clickup.tasks_completed}
    in_progress_statuses = {"in progress", "in review", "review", "in development"}

    candidates = [
        t for t in activity.clickup.status_changes
        if t.status.lower() in in_progress_statuses
        and t.task_id not in completed_ids
        and t.parent_id is None
    ]

    items = []
    for t in candidates[:3]:
        prefix = _status_prefix(t.status)
        label = f"{prefix}: " if prefix else "pick: "
        items.append(_section(_text(label), _link(t.url, t.name)))

    return items


def _build_manual_elements(manual_updates: List[str]) -> List[Dict[str, Any]]:
    """Build Block Kit elements for user-authored manual updates."""
    if not manual_updates:
        return []
    items = []
    for text in manual_updates[:20]:
        clean = " ".join(str(text).split()).strip()
        if not clean:
            continue
        if len(clean) > 180:
            clean = clean[:179].rstrip() + "…"
        items.append(_section(_text(clean)))
    if not items:
        return []
    return [_list_block(1, items)]


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def generate_summary_blocks(activity: DailyActivity) -> List[Dict[str, Any]]:
    """
    Build a Slack Block Kit ``rich_text`` block for the EOD summary.

    Returns a list of block dicts ready to pass to ``chat.postMessage(blocks=...)``.
    """
    logger.info("Generating EOD summary for %s", activity.date)

    rt_elements: List[Dict[str, Any]] = []

    # Header: "Updates:"
    rt_elements.append(_section(_text("Updates:", bold=True)))

    # --- Development ---
    gh_elements = _build_github_elements(activity.github)
    if gh_elements:
        rt_elements.append(_list_block(0, [_section(_text("Development:", bold=True))]))
        rt_elements.extend(gh_elements)

    # --- Task updates ---
    cu_elements = _build_clickup_elements(activity.clickup)
    if cu_elements:
        rt_elements.append(_list_block(0, [_section(_text("Task updates:", bold=True))]))
        rt_elements.extend(cu_elements)

    # --- Manual updates ---
    manual_elements = _build_manual_elements(activity.manual_updates)
    if manual_elements:
        rt_elements.append(_list_block(0, [_section(_text("Additional updates:", bold=True))]))
        rt_elements.extend(manual_elements)

    # Empty state
    if len(rt_elements) == 1:
        rt_elements.append(_list_block(0, [_section(_text("No tracked activity today.", italic=True))]))

    # --- Next ---
    next_items = _build_next_elements(activity)
    if next_items:
        rt_elements.append(_section(_text("Next:", bold=True)))
        rt_elements.append(_list_block(0, next_items))

    blocks = [{"type": "rich_text", "elements": rt_elements}]

    logger.debug("Summary blocks generated (%d elements)", len(rt_elements))
    return blocks


def generate_summary(activity: DailyActivity) -> str:
    """
    Generate a plain-text fallback summary.

    This is used as the ``text`` parameter in chat.postMessage (shown in
    notifications and non-Block-Kit clients).
    """
    parts = ["Updates:"]

    if activity.github.commits or activity.github.prs_opened or activity.github.prs_merged:
        parts.append(f"Development: {len(activity.github.commits)} commits, "
                     f"{len(activity.github.prs_opened)} PRs opened, "
                     f"{len(activity.github.prs_merged)} PRs merged")

    if activity.clickup.tasks_completed:
        parts.append(f"Completed: {len(activity.clickup.tasks_completed)} tasks")
    if activity.clickup.status_changes:
        parts.append(f"In progress: {len(activity.clickup.status_changes)} tasks")
    if activity.manual_updates:
        parts.append(f"Additional updates: {len(activity.manual_updates)}")

    return " | ".join(parts)
