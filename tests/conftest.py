"""
Shared test fixtures.

Sets environment variables *before* any application module is imported
so ``Settings`` can be instantiated without a real ``.env`` file.
"""

import os

import pytest

# Populate required env vars with safe dummy values for test isolation.
_TEST_ENV = {
    "GITHUB_TOKEN": "ghp_test_token_000000000000000000000",
    "GITHUB_USERNAME": "testuser",
    "CLICKUP_API_TOKEN": "pk_test_000000000000000000",
    "CLICKUP_TEAM_ID": "12345678",
    "CLICKUP_USER_ID": "99999999",
    "SLACK_BOT_TOKEN": "xoxb-test-000000000000-0000000000000-xxxxxxxxxxxxxxxxxxxx",
    "SLACK_CHANNEL": "#test-eod",
    "REPORT_HOUR": "18",
    "REPORT_MINUTE": "0",
    "LOG_LEVEL": "DEBUG",
    "APP_ENV": "test",
    "TIMEZONE": "UTC",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)
