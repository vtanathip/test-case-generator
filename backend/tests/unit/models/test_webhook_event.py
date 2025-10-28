"""Unit tests for WebhookEvent model."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.webhook_event import WebhookEvent


class TestWebhookEventValidation:
    """Test WebhookEvent model validation rules."""

    def test_create_valid_webhook_event(self):
        """Test creating a valid webhook event."""
        event = WebhookEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            event_type="issues.opened",
            issue_number=123,
            issue_title="Add authentication feature",
            issue_body="Implement OAuth2 authentication with Google provider.",
            labels=["generate-tests", "enhancement"],
            repository="owner/repo",
            signature="sha256=abc123def456",
            received_at=datetime.now(),
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )

        assert event.event_id == "550e8400-e29b-41d4-a716-446655440000"
        assert event.event_type == "issues.opened"
        assert event.issue_number == 123
        assert "generate-tests" in event.labels

    def test_event_type_validation(self):
        """Test event_type must be issues.opened or issues.labeled."""
        valid_data = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "issues.opened",
            "issue_number": 123,
            "issue_title": "Test issue",
            "issue_body": "Test body",
            "labels": ["generate-tests"],
            "repository": "owner/repo",
            "signature": "sha256=test",
            "received_at": datetime.now(),
            "correlation_id": "660e8400-e29b-41d4-a716-446655440001"
        }

        # Valid: issues.opened
        event = WebhookEvent(**valid_data)
        assert event.event_type == "issues.opened"

        # Valid: issues.labeled
        valid_data["event_type"] = "issues.labeled"
        event = WebhookEvent(**valid_data)
        assert event.event_type == "issues.labeled"

        # Invalid: other event type
        with pytest.raises(ValidationError) as exc_info:
            valid_data["event_type"] = "pull_request.opened"
            WebhookEvent(**valid_data)
        assert "event_type" in str(exc_info.value)

    def test_issue_title_max_length(self):
        """Test issue_title is limited to 256 characters."""
        valid_data = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "issues.opened",
            "issue_number": 123,
            "issue_title": "x" * 256,  # Exactly 256 chars
            "issue_body": "Test body",
            "labels": ["generate-tests"],
            "repository": "owner/repo",
            "signature": "sha256=test",
            "received_at": datetime.now(),
            "correlation_id": "660e8400-e29b-41d4-a716-446655440001"
        }

        # Should succeed at 256 chars
        event = WebhookEvent(**valid_data)
        assert len(event.issue_title) == 256

        # Should fail above 256 chars
        with pytest.raises(ValidationError) as exc_info:
            valid_data["issue_title"] = "x" * 257
            WebhookEvent(**valid_data)
        assert "issue_title" in str(exc_info.value)

    def test_issue_body_truncation(self):
        """Test issue_body is truncated to 5000 characters with warning."""
        long_body = "x" * 6000

        event = WebhookEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            event_type="issues.opened",
            issue_number=123,
            issue_title="Test",
            issue_body=long_body,
            labels=["generate-tests"],
            repository="owner/repo",
            signature="sha256=test",
            received_at=datetime.now(),
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )

        # Should be truncated to 5000 chars
        assert len(event.issue_body) == 5000
        assert event.issue_body == long_body[:5000]

    def test_labels_must_contain_generate_tests(self):
        """Test labels validation requires 'generate-tests' tag."""
        valid_data = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "issues.opened",
            "issue_number": 123,
            "issue_title": "Test",
            "issue_body": "Body",
            "labels": ["generate-tests", "bug"],
            "repository": "owner/repo",
            "signature": "sha256=test",
            "received_at": datetime.now(),
            "correlation_id": "660e8400-e29b-41d4-a716-446655440001"
        }

        # Should succeed with generate-tests label
        event = WebhookEvent(**valid_data)
        assert "generate-tests" in event.labels

        # Should fail without generate-tests label
        with pytest.raises(ValidationError) as exc_info:
            valid_data["labels"] = ["bug", "enhancement"]
            WebhookEvent(**valid_data)
        assert "generate-tests" in str(exc_info.value).lower()

    def test_signature_format(self):
        """Test signature must be valid HMAC-SHA256 format."""
        valid_data = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "issues.opened",
            "issue_number": 123,
            "issue_title": "Test",
            "issue_body": "Body",
            "labels": ["generate-tests"],
            "repository": "owner/repo",
            "signature": "sha256=abcdef1234567890",
            "received_at": datetime.now(),
            "correlation_id": "660e8400-e29b-41d4-a716-446655440001"
        }

        # Valid sha256= prefix
        event = WebhookEvent(**valid_data)
        assert event.signature.startswith("sha256=")

        # Invalid format (missing sha256= prefix)
        with pytest.raises(ValidationError) as exc_info:
            valid_data["signature"] = "abcdef1234567890"
            WebhookEvent(**valid_data)
        assert "signature" in str(exc_info.value).lower()

    def test_repository_format(self):
        """Test repository must be in 'owner/repo' format."""
        valid_data = {
            "event_id": "550e8400-e29b-41d4-a716-446655440000",
            "event_type": "issues.opened",
            "issue_number": 123,
            "issue_title": "Test",
            "issue_body": "Body",
            "labels": ["generate-tests"],
            "repository": "owner/repo",
            "signature": "sha256=test",
            "received_at": datetime.now(),
            "correlation_id": "660e8400-e29b-41d4-a716-446655440001"
        }

        # Valid format
        event = WebhookEvent(**valid_data)
        assert "/" in event.repository

        # Invalid format (no slash)
        with pytest.raises(ValidationError) as exc_info:
            valid_data["repository"] = "invalid-format"
            WebhookEvent(**valid_data)
        assert "repository" in str(exc_info.value).lower()

    def test_webhook_event_immutability(self):
        """Test WebhookEvent is immutable once created."""
        event = WebhookEvent(
            event_id="550e8400-e29b-41d4-a716-446655440000",
            event_type="issues.opened",
            issue_number=123,
            issue_title="Test",
            issue_body="Body",
            labels=["generate-tests"],
            repository="owner/repo",
            signature="sha256=test",
            received_at=datetime.now(),
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )

        # Should not allow modification
        with pytest.raises(ValidationError):
            event.issue_number = 456
