"""
Tests for the Slack service — verifies message sending and OOO detection.

All Slack API calls are mocked so no real tokens or network access is needed.
"""

from unittest.mock import MagicMock, patch

from app.services import slack_service


class TestSendMessage:
    """Verify ``send_message`` behaviour under various conditions."""

    @patch.object(slack_service, "_client")
    def test_success(self, mock_client: MagicMock) -> None:
        slack_service._cached_identity = ("", "")  # reset cache
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "123.456"}
        assert slack_service.send_message("#test", "Hello") is True
        mock_client.chat_postMessage.assert_called_once()

    @patch.object(slack_service, "_client")
    def test_api_error(self, mock_client: MagicMock) -> None:
        slack_service._cached_identity = ("", "")  # reset cache
        from slack_sdk.errors import SlackApiError

        mock_client.chat_postMessage.side_effect = SlackApiError(
            message="channel_not_found",
            response=MagicMock(
                __getitem__=lambda self, k: {"error": "channel_not_found", "response_metadata": {}}.get(k, ""),
                get=lambda k, d=None: {"error": "channel_not_found", "response_metadata": {}}.get(k, d),
            ),
        )
        assert slack_service.send_message("#invalid", "Hello") is False


class TestOOODetection:
    """Verify OOO status checking logic."""

    @patch.object(slack_service, "_client")
    def test_user_is_ooo_by_text(self, mock_client: MagicMock) -> None:
        mock_client.auth_test.return_value = {"user_id": "U123"}
        mock_client.users_profile_get.return_value = {
            "profile": {"status_text": "OOO until Monday", "status_emoji": ""}
        }
        assert slack_service.is_user_ooo() is True

    @patch.object(slack_service, "_client")
    def test_user_is_ooo_by_emoji(self, mock_client: MagicMock) -> None:
        mock_client.auth_test.return_value = {"user_id": "U123"}
        mock_client.users_profile_get.return_value = {
            "profile": {"status_text": "", "status_emoji": ":palm_tree:"}
        }
        assert slack_service.is_user_ooo() is True

    @patch.object(slack_service, "_client")
    def test_user_is_not_ooo(self, mock_client: MagicMock) -> None:
        mock_client.auth_test.return_value = {"user_id": "U123"}
        mock_client.users_profile_get.return_value = {
            "profile": {"status_text": "Focusing", "status_emoji": ":headphones:"}
        }
        assert slack_service.is_user_ooo() is False
