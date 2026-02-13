"""
Tests for FastAPI endpoints.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Verify the health check endpoint."""

    def test_health_returns_ok(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"


class TestTriggerEndpoint:
    """Verify the manual trigger endpoint."""

    @patch("app.main.run_eod_pipeline")
    def test_trigger_returns_accepted(self, mock_pipeline) -> None:
        mock_pipeline.return_value = "summary"
        response = client.post("/trigger-eod")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "background" in data["message"].lower()
