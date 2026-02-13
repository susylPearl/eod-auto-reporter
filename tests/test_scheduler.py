"""
Tests for the scheduler and EOD pipeline.
"""

from unittest.mock import MagicMock, patch

from app.scheduler import run_eod_pipeline


class TestEODPipeline:
    """Verify the orchestration logic of the EOD pipeline."""

    @patch("app.scheduler.slack_service")
    @patch("app.scheduler.summary_service")
    @patch("app.scheduler.clickup_service")
    @patch("app.scheduler.github_service")
    def test_full_pipeline(
        self,
        mock_gh: MagicMock,
        mock_cu: MagicMock,
        mock_summary: MagicMock,
        mock_slack: MagicMock,
    ) -> None:
        """Pipeline should call all services in order and post to Slack."""
        from app.models.activity_models import ClickUpActivity, GitHubActivity

        mock_gh.fetch_github_activity.return_value = GitHubActivity()
        mock_cu.fetch_clickup_activity.return_value = ClickUpActivity()
        mock_summary.generate_summary_blocks.return_value = [{"type": "rich_text", "elements": []}]
        mock_summary.generate_summary.return_value = "Test summary"
        mock_slack.is_user_ooo.return_value = False
        mock_slack.send_message.return_value = True

        result = run_eod_pipeline()

        assert result == "Test summary"
        mock_gh.fetch_github_activity.assert_called_once()
        mock_cu.fetch_clickup_activity.assert_called_once()
        mock_summary.generate_summary_blocks.assert_called_once()
        mock_summary.generate_summary.assert_called_once()
        mock_slack.send_message.assert_called_once()

    @patch("app.scheduler.slack_service")
    def test_skip_when_ooo(self, mock_slack: MagicMock) -> None:
        """Pipeline should skip entirely when user is OOO."""
        mock_slack.is_user_ooo.return_value = True

        result = run_eod_pipeline()

        assert "OOO" in result
        mock_slack.send_message.assert_not_called()
