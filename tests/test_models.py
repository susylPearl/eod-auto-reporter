"""
Tests for the activity data models.

Validates serialization, defaults, and edge cases.
"""

from datetime import datetime, timezone

from app.models.activity_models import (
    ClickUpActivity,
    ClickUpTask,
    DailyActivity,
    GitHubActivity,
    GitHubCommit,
    GitHubPR,
)


class TestGitHubModels:
    """Validate GitHub domain models."""

    def test_commit_creation(self) -> None:
        commit = GitHubCommit(
            sha="abc123",
            message="feat: add login",
            repo="org/app",
            url="https://github.com/org/app/commit/abc123",
            timestamp=datetime.now(timezone.utc),
        )
        assert commit.sha == "abc123"
        assert commit.message == "feat: add login"

    def test_pr_optional_merged_at(self) -> None:
        pr = GitHubPR(
            number=1,
            title="WIP",
            repo="org/app",
            state="open",
            url="https://github.com/org/app/pull/1",
            created_at=datetime.now(timezone.utc),
        )
        assert pr.merged_at is None

    def test_activity_defaults(self) -> None:
        activity = GitHubActivity()
        assert activity.commits == []
        assert activity.prs_opened == []
        assert activity.prs_merged == []


class TestClickUpModels:
    """Validate ClickUp domain models."""

    def test_task_creation(self) -> None:
        task = ClickUpTask(
            task_id="t1",
            name="Do thing",
            status="open",
            url="https://app.clickup.com/t/t1",
            date_updated=datetime.now(timezone.utc),
        )
        assert task.task_id == "t1"
        assert task.previous_status is None

    def test_activity_defaults(self) -> None:
        activity = ClickUpActivity()
        assert activity.tasks_updated == []
        assert activity.comments == []


class TestDailyActivity:
    """Validate the unified model."""

    def test_combined_defaults(self) -> None:
        daily = DailyActivity(date="2026-02-13")
        assert daily.github.commits == []
        assert daily.clickup.tasks_updated == []

    def test_serialization_round_trip(self) -> None:
        daily = DailyActivity(
            date="2026-02-13",
            github=GitHubActivity(
                commits=[
                    GitHubCommit(
                        sha="aaa",
                        message="init",
                        repo="o/r",
                        url="https://github.com/o/r/commit/aaa",
                        timestamp=datetime(2026, 2, 13, 12, 0, tzinfo=timezone.utc),
                    )
                ]
            ),
        )
        data = daily.model_dump()
        restored = DailyActivity.model_validate(data)
        assert restored.github.commits[0].sha == "aaa"
