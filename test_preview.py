"""
Quick preview script — generates a sample EOD summary with mock data.

Usage:
  python test_preview.py          # Print to terminal only
  python test_preview.py --send   # Print AND send to your Slack channel
"""

import sys
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
from app.services.summary_service import generate_summary

now = datetime.now(timezone.utc)
today = now.strftime("%Y-%m-%d")

# --- Mock data --------------------------------------------------------

mock_activity = DailyActivity(
    date=today,
    github=GitHubActivity(
        commits=[
            GitHubCommit(
                sha="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
                message="fix: resolve auth token refresh race condition",
                repo="myorg/backend-api",
                url="https://github.com/myorg/backend-api/commit/a1b2c3d",
                timestamp=now,
            ),
            GitHubCommit(
                sha="f7e8d9c0b1a2f7e8d9c0b1a2f7e8d9c0b1a2f7e8",
                message="feat: add rate limiting middleware",
                repo="myorg/backend-api",
                url="https://github.com/myorg/backend-api/commit/f7e8d9c",
                timestamp=now,
            ),
            GitHubCommit(
                sha="1234567890abcdef1234567890abcdef12345678",
                message="chore: bump dependencies to latest versions",
                repo="myorg/infra-config",
                url="https://github.com/myorg/infra-config/commit/1234567",
                timestamp=now,
            ),
        ],
        prs_opened=[
            GitHubPR(
                number=187,
                title="Add rate limiting middleware for API endpoints",
                repo="myorg/backend-api",
                state="open",
                url="https://github.com/myorg/backend-api/pull/187",
                created_at=now,
            ),
        ],
        prs_merged=[
            GitHubPR(
                number=182,
                title="Fix auth token refresh race condition",
                repo="myorg/backend-api",
                state="merged",
                url="https://github.com/myorg/backend-api/pull/182",
                created_at=now,
                merged_at=now,
            ),
        ],
    ),
    clickup=ClickUpActivity(
        tasks_updated=[
            ClickUpTask(
                task_id="abc123",
                name="Implement user session management",
                status="in progress",
                url="https://app.clickup.com/t/abc123",
                date_updated=now,
            ),
            ClickUpTask(
                task_id="def456",
                name="Write API rate limiting tests",
                status="review",
                url="https://app.clickup.com/t/def456",
                date_updated=now,
            ),
        ],
        tasks_completed=[
            ClickUpTask(
                task_id="ghi789",
                name="Fix token refresh bug",
                status="done",
                url="https://app.clickup.com/t/ghi789",
                date_updated=now,
            ),
        ],
        status_changes=[
            ClickUpTask(
                task_id="def456",
                name="Write API rate limiting tests",
                status="review",
                previous_status="in progress",
                url="https://app.clickup.com/t/def456",
                date_updated=now,
            ),
        ],
        comments=[
            ClickUpComment(
                task_id="abc123",
                task_name="Implement user session management",
                comment_text="Updated the session store to use Redis — need review on the TTL config",
                date=now,
            ),
        ],
    ),
)

# --- Generate & print -------------------------------------------------

summary = generate_summary(mock_activity)

print("=" * 60)
print("  PREVIEW — This is how your EOD message will look")
print("=" * 60)
print()
print(summary)
print()
print("=" * 60)

# --- Optionally send to Slack -----------------------------------------

if "--send" in sys.argv:
    from app.config import settings
    from app.services.slack_service import send_message

    print()
    print(f"Sending to Slack channel: {settings.slack_channel}")
    success = send_message(settings.slack_channel, summary)
    if success:
        print("Sent successfully! Check your Slack channel.")
    else:
        print("Failed to send. Check the logs above for errors.")
else:
    print()
    print("To send this to Slack, run:")
    print("  python test_preview.py --send")
