"""Unit tests for WebhookService."""
import hashlib
import hmac
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.exceptions import (
    DuplicateWebhookError,
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
)
from src.services.webhook_service import WebhookService


class TestWebhookServiceValidation:
    """Test WebhookService signature validation and event processing."""

    @pytest.fixture
    def webhook_secret(self):
        """Fixture for webhook secret."""
        return "test_webhook_secret_key_12345"

    @pytest.fixture
    def webhook_service(self, webhook_secret):
        """Fixture for WebhookService instance."""
        # Mock dependencies
        mock_redis = AsyncMock()
        # Default: no duplicates (exists returns False)
        mock_redis.exists = AsyncMock(return_value=False)
        mock_redis.set_with_ttl = AsyncMock()

        mock_config = Mock()
        mock_config.github_webhook_secret = webhook_secret

        return WebhookService(redis_client=mock_redis, config=mock_config)

    @pytest.fixture
    def valid_webhook_payload(self):
        """Fixture for valid GitHub webhook payload."""
        return {
            "action": "opened",
            "issue": {
                "number": 42,
                "title": "Add OAuth2 authentication feature",
                "body": "Implement OAuth2 authentication with Google provider.",
                "labels": [
                    {"name": "generate-tests"},
                    {"name": "enhancement"}
                ]
            },
            "repository": {
                "full_name": "owner/repo"
            }
        }

    def test_valid_signature_validation(self, webhook_service, webhook_secret, valid_webhook_payload):
        """Test HMAC-SHA256 signature validation accepts valid signature."""
        import json

        # Generate valid signature
        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Should not raise exception
        is_valid = webhook_service.validate_signature(
            payload=payload_bytes,
            signature=signature_header
        )

        assert is_valid is True

    def test_invalid_signature_rejected(self, webhook_service, valid_webhook_payload):
        """Test invalid signature is rejected with InvalidWebhookSignatureError."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        invalid_signature = "sha256=invalid_signature_hash_12345"

        # Should raise InvalidWebhookSignatureError (E101)
        with pytest.raises(InvalidWebhookSignatureError) as exc_info:
            webhook_service.validate_signature(
                payload=payload_bytes,
                signature=invalid_signature
            )

        assert exc_info.value.error_code == "E101"

    def test_missing_signature_rejected(self, webhook_service, valid_webhook_payload):
        """Test missing signature header is rejected."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')

        with pytest.raises(InvalidWebhookSignatureError) as exc_info:
            webhook_service.validate_signature(
                payload=payload_bytes,
                signature=None
            )

        assert exc_info.value.error_code == "E101"

    def test_malformed_signature_format(self, webhook_service, valid_webhook_payload):
        """Test signature without 'sha256=' prefix is rejected."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        malformed_signatures = [
            "invalid_format",
            "sha1=abc123",
            "abc123",
            ""
        ]

        for malformed in malformed_signatures:
            with pytest.raises(InvalidWebhookSignatureError):
                webhook_service.validate_signature(
                    payload=payload_bytes,
                    signature=malformed
                )

    @pytest.mark.asyncio
    async def test_generate_tests_tag_required(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test 'generate-tests' label is required (FR-002)."""
        import json

        # Valid payload with generate-tests label
        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Should process successfully
        webhook_event = await webhook_service.process_webhook(
            payload=payload_bytes,
            signature=signature_header,
            event_type="issues.opened"
        )

        assert "generate-tests" in webhook_event.labels

        # Invalid: Missing generate-tests label
        invalid_payload = {
            **valid_webhook_payload,
            "issue": {
                **valid_webhook_payload["issue"],
                "labels": [{"name": "enhancement"}]
            }
        }

        invalid_bytes = json.dumps(invalid_payload).encode('utf-8')
        invalid_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            invalid_bytes,
            hashlib.sha256
        ).hexdigest()

        # Should raise InvalidWebhookPayloadError (E103)
        with pytest.raises(InvalidWebhookPayloadError) as exc_info:
            await webhook_service.process_webhook(
                payload=invalid_bytes,
                signature=f"sha256={invalid_signature}",
                event_type="issues.opened"
            )

        assert exc_info.value.error_code == "E103"
        assert "generate-tests" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_duplicate_webhook_detection(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test duplicate webhook is detected via idempotency key (FR-017)."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Mock Redis to return existing idempotency key
        webhook_service.redis_client.exists = AsyncMock(return_value=True)

        # Should raise DuplicateWebhookError (E104)
        with pytest.raises(DuplicateWebhookError) as exc_info:
            await webhook_service.process_webhook(
                payload=payload_bytes,
                signature=signature_header,
                event_type="issues.opened"
            )

        assert exc_info.value.error_code == "E104"

    @pytest.mark.asyncio
    async def test_event_parsing_from_payload(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test WebhookEvent is correctly parsed from GitHub payload."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Mock Redis to allow processing
        webhook_service.redis_client.exists = AsyncMock(return_value=False)
        webhook_service.redis_client.set_with_ttl = AsyncMock()

        webhook_event = await webhook_service.process_webhook(
            payload=payload_bytes,
            signature=signature_header,
            event_type="issues.opened"
        )

        # Verify WebhookEvent attributes
        assert webhook_event.event_type == "issues.opened"
        assert webhook_event.issue_number == 42
        assert webhook_event.issue_title == "Add OAuth2 authentication feature"
        assert webhook_event.repository == "owner/repo"
        assert "generate-tests" in webhook_event.labels

    @pytest.mark.asyncio
    async def test_event_type_validation(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test only 'issues.opened' and 'issues.labeled' event types are accepted."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Mock Redis
        webhook_service.redis_client.exists = AsyncMock(return_value=False)
        webhook_service.redis_client.set_with_ttl = AsyncMock()

        # Valid event types
        valid_types = ["issues.opened", "issues.labeled"]
        for event_type in valid_types:
            webhook_event = await webhook_service.process_webhook(
                payload=payload_bytes,
                signature=signature_header,
                event_type=event_type
            )
            assert webhook_event.event_type == event_type

        # Invalid event type
        with pytest.raises(InvalidWebhookPayloadError):
            await webhook_service.process_webhook(
                payload=payload_bytes,
                signature=signature_header,
                event_type="issues.closed"
            )

    @pytest.mark.asyncio
    async def test_idempotency_key_generation(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test idempotency key is SHA256 hash of (repository + issue_number)."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Mock Redis
        webhook_service.redis_client.exists = AsyncMock(return_value=False)
        webhook_service.redis_client.set_with_ttl = AsyncMock()

        webhook_event = await webhook_service.process_webhook(
            payload=payload_bytes,
            signature=signature_header,
            event_type="issues.opened"
        )

        # Calculate expected idempotency key
        key_string = f"{valid_webhook_payload['repository']['full_name']}-{valid_webhook_payload['issue']['number']}"
        expected_key = hashlib.sha256(key_string.encode('utf-8')).hexdigest()

        # Verify Redis set_with_ttl was called with correct key
        webhook_service.redis_client.set_with_ttl.assert_called_once()
        call_args = webhook_service.redis_client.set_with_ttl.call_args[0]
        assert expected_key in call_args[0]  # Key contains hash

    @pytest.mark.asyncio
    async def test_malformed_payload_rejected(self, webhook_service, webhook_secret):
        """Test malformed JSON payload is rejected."""
        # Missing required fields
        malformed_payloads = [
            {},  # Empty
            {"action": "opened"},  # Missing issue
            {"issue": {"number": 42}},  # Missing repository
            {"issue": {}, "repository": {}},  # Missing fields in nested objects
        ]

        for malformed in malformed_payloads:
            import json
            payload_bytes = json.dumps(malformed).encode('utf-8')
            expected_signature = hmac.new(
                webhook_secret.encode('utf-8'),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            signature_header = f"sha256={expected_signature}"

            with pytest.raises(InvalidWebhookPayloadError):
                await webhook_service.process_webhook(
                    payload=payload_bytes,
                    signature=signature_header,
                    event_type="issues.opened"
                )

    @pytest.mark.asyncio
    async def test_correlation_id_generation(self, webhook_service, valid_webhook_payload, webhook_secret):
        """Test correlation ID is generated for each webhook event."""
        import json

        payload_bytes = json.dumps(valid_webhook_payload).encode('utf-8')
        expected_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        signature_header = f"sha256={expected_signature}"

        # Mock Redis
        webhook_service.redis_client.exists = AsyncMock(return_value=False)
        webhook_service.redis_client.set_with_ttl = AsyncMock()

        webhook_event = await webhook_service.process_webhook(
            payload=payload_bytes,
            signature=signature_header,
            event_type="issues.opened"
        )

        # Verify correlation_id is a valid UUID
        import uuid
        assert uuid.UUID(webhook_event.correlation_id)
