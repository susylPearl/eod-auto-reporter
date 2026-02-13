"""
Tests for the summary service.

Tests both the Block Kit output (``generate_summary_blocks``) and the
plain-text fallback (``generate_summary``).
"""

import json
from datetime import datetime, timezone

from app.models.activity_models import (
    ClickUpActivity,
    ClickUpComment,
    ClickUpTask,
    DailyActivity,
    GitHubActivity,
    GitHubCommit,
    GitHubPR,
)
from app.services.summary_service import generate_summary, generate_summary_blocks


def _make_commit(msg: str = "fix: resolve flaky test", repo: str = "org/backend") -> GitHubCommit:
    return GitHubCommit(
        sha="abc1234567890abcdef1234567890abcdef123456",
        message=msg,
        repo=repo,
        url=f"https://github.com/{repo}/commit/abc1234",
        timestamp=datetime.now(timezone.utc),
    )


def _make_pr(title: str = "Add caching layer", number: int = 42, state: str = "open") -> GitHubPR:
    return GitHubPR(
        number=number,
        title=title,
        repo="org/backend",
        state=state,
        url=f"https://github.com/org/backend/pull/{number}",
        created_at=datetime.now(timezone.utc),
    )


def _make_task(name: str = "Implement auth", status: str = "in progress", task_id: str = "abc123") -> ClickUpTask:
    return ClickUpTask(
        task_id=task_id,
        name=name,
        status=status,
        url=f"https://app.clickup.com/t/{task_id}",
        date_updated=datetime.now(timezone.utc),
    )


def _blocks_to_text(blocks: list) -> str:
    """Flatten Block Kit blocks to a searchable string for assertions."""
    return json.dumps(blocks)


class TestGenerateSummaryBlocks:
    """Test suite for ``generate_summary_blocks`` (Block Kit output)."""

    def test_full_activity(self) -> None:
        """Blocks should contain all sections when activity is present."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(
                commits=[_make_commit()],
                prs_opened=[_make_pr()],
                prs_merged=[_make_pr(title="Merged PR", number=43, state="merged")],
            ),
            clickup=ClickUpActivity(
                tasks_updated=[_make_task()],
                tasks_completed=[_make_task(name="Write tests", status="done", task_id="ghi789")],
                status_changes=[],
                comments=[
                    ClickUpComment(
                        task_id="abc123",
                        task_name="Implement auth",
                        comment_text="Addressed review feedback",
                        date=datetime.now(timezone.utc),
                    )
                ],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "rich_text" in text
        assert "Development:" in text
        assert "Task updates:" in text
        assert "resolve flaky test" in text
        assert "Add caching layer" in text
        assert "Merged PR" in text
        assert "Write tests" in text
        assert "Addressed review feedback" in text

    def test_empty_activity(self) -> None:
        """When nothing happened the blocks should say so gracefully."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "Updates:" in text
        assert "No tracked activity today" in text

    def test_github_only(self) -> None:
        """Blocks with GitHub activity but no ClickUp."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(
                commits=[_make_commit(), _make_commit("chore: bump deps")],
                prs_opened=[],
                prs_merged=[],
            ),
            clickup=ClickUpActivity(),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "Development:" in text
        assert "resolve flaky test" in text
        assert "bump deps" in text

    def test_clickup_only(self) -> None:
        """Blocks with ClickUp activity but no GitHub."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(
                tasks_updated=[_make_task()],
                tasks_completed=[],
                status_changes=[_make_task(status="review", task_id="def456")],
                comments=[],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "Task updates:" in text
        assert "Implement auth" in text

    def test_status_prefix_wip(self) -> None:
        """In-progress tasks should get 'wip:' prefix in blocks."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(
                tasks_updated=[_make_task(status="in progress")],
                tasks_completed=[],
                status_changes=[_make_task(status="in progress")],
                comments=[],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)
        assert "wip:" in text

    def test_status_prefix_completed(self) -> None:
        """Completed tasks should get 'completed:' prefix in blocks."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(
                tasks_updated=[],
                tasks_completed=[_make_task(name="Done task", status="done")],
                status_changes=[],
                comments=[],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)
        assert "completed:" in text

    def test_next_section_for_in_progress(self) -> None:
        """In-progress top-level tasks should appear in the Next section."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(
                tasks_updated=[_make_task(name="WIP task", status="in progress")],
                tasks_completed=[],
                status_changes=[_make_task(name="WIP task", status="in progress")],
                comments=[],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)
        assert "Next:" in text
        assert "WIP task" in text

    def test_subtask_hierarchy(self) -> None:
        """Subtasks should be nested under their parent in the blocks."""
        parent = _make_task(name="Parent task", status="in progress", task_id="p1")
        child = ClickUpTask(
            task_id="c1",
            name="Child subtask",
            status="in progress",
            parent_id="p1",
            url="https://app.clickup.com/t/c1",
            date_updated=datetime.now(timezone.utc),
        )

        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(
                tasks_updated=[parent, child],
                tasks_completed=[],
                status_changes=[parent, child],
                comments=[],
            ),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "Parent task" in text
        assert "Child subtask" in text
        # Child should be at indent 2
        assert '"indent": 2' in text

    def test_multi_repo_grouping(self) -> None:
        """Commits from multiple repos should be grouped by repo."""
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(
                commits=[
                    _make_commit("fix in frontend", "org/frontend"),
                    _make_commit("fix in backend", "org/backend"),
                ],
                prs_opened=[],
                prs_merged=[],
            ),
            clickup=ClickUpActivity(),
        )

        blocks = generate_summary_blocks(activity)
        text = _blocks_to_text(blocks)

        assert "frontend" in text
        assert "backend" in text


class TestGenerateSummaryFallback:
    """Test suite for ``generate_summary`` (plain-text fallback)."""

    def test_fallback_contains_updates(self) -> None:
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(),
            clickup=ClickUpActivity(),
        )
        result = generate_summary(activity)
        assert "Updates:" in result

    def test_fallback_shows_counts(self) -> None:
        activity = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(
                commits=[_make_commit()],
                prs_opened=[_make_pr()],
                prs_merged=[],
            ),
            clickup=ClickUpActivity(
                tasks_updated=[],
                tasks_completed=[_make_task(status="done")],
                status_changes=[],
                comments=[],
            ),
        )
        result = generate_summary(activity)
        assert "1 commits" in result
        assert "1 PRs opened" in result
        assert "Completed: 1 tasks" in result
