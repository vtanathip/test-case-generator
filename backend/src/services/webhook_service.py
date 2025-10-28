"""WebhookService for validating and processing GitHub webhooks."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime
from typing import Literal

from src.core.exceptions import (
    DuplicateWebhookError,
    InvalidWebhookPayloadError,
    InvalidWebhookSignatureError,
)
from src.models.webhook_event import WebhookEvent


class WebhookService:
    """Service for validating and processing GitHub webhook events."""

    def __init__(self, redis_client, config):
        """Initialize WebhookService with Redis client and config.
        
        Args:
            redis_client: Redis client for idempotency checks
            config: Configuration object with github_webhook_secret
        """
        self.redis_client = redis_client
        self.config = config
        self.webhook_secret = config.github_webhook_secret

    def validate_signature(self, payload: bytes, signature: str | None) -> bool:
        """Validate HMAC-SHA256 signature from GitHub webhook.
        
        Args:
            payload: Raw webhook payload bytes
            signature: Signature header from GitHub (sha256=...)
            
        Returns:
            True if signature is valid
            
        Raises:
            InvalidWebhookSignatureError: If signature is invalid or missing (E101)
        """
        if not signature:
            raise InvalidWebhookSignatureError(
                expected="sha256=...",
                received="None"
            )

        # Validate signature format
        if not signature.startswith("sha256="):
            raise InvalidWebhookSignatureError(
                expected="sha256=...",
                received=signature
            )

        # Extract hash from signature
        received_hash = signature[7:]  # Remove 'sha256=' prefix

        # Calculate expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(received_hash, expected_signature):
            raise InvalidWebhookSignatureError(
                expected=expected_signature,
                received=received_hash
            )

        return True

    async def process_webhook(
        self,
        payload: bytes,
        signature: str,
        event_type: str
    ) -> WebhookEvent:
        """Process GitHub webhook and create WebhookEvent.
        
        Args:
            payload: Raw webhook payload bytes
            signature: HMAC-SHA256 signature from GitHub
            event_type: GitHub event type (issues.opened, issues.labeled)
            
        Returns:
            WebhookEvent: Validated webhook event
            
        Raises:
            InvalidWebhookSignatureError: If signature validation fails (E101)
            InvalidWebhookPayloadError: If payload is invalid or missing required fields (E102/E103)
            DuplicateWebhookError: If webhook already processed (E104)
        """
        # Step 1: Validate signature
        self.validate_signature(payload, signature)

        # Step 2: Parse JSON payload
        try:
            payload_dict = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise InvalidWebhookPayloadError(
                message=f"Invalid JSON payload: {str(e)}",
                error_code="E102"
            )

        # Step 3: Validate event type
        valid_event_types = ["issues.opened", "issues.labeled"]
        if event_type not in valid_event_types:
            raise InvalidWebhookPayloadError(
                message=f"Unsupported event type: {event_type}. Supported: {valid_event_types}",
                error_code="E102"
            )

        # Step 4: Extract required fields
        try:
            issue = payload_dict["issue"]
            issue_number = issue["number"]
            issue_title = issue["title"]
            issue_body = issue.get("body", "")
            repository = payload_dict["repository"]["full_name"]

            # Extract labels
            labels = [label["name"] for label in issue.get("labels", [])]

        except (KeyError, TypeError) as e:
            raise InvalidWebhookPayloadError(
                message=f"Missing required field in payload: {str(e)}",
                error_code="E102"
            )

        # Step 5: Validate generate-tests label is present (FR-002)
        if "generate-tests" not in labels:
            raise InvalidWebhookPayloadError(
                message="Missing required label 'generate-tests' (FR-002)",
                error_code="E103"
            )

        # Step 6: Generate idempotency key (SHA256 of repository + issue_number)
        key_string = f"{repository}-{issue_number}"
        idempotency_key = hashlib.sha256(key_string.encode('utf-8')).hexdigest()

        # Step 7: Check for duplicate webhook (idempotency)
        is_duplicate = await self.redis_client.exists(f"webhook:{idempotency_key}")
        if is_duplicate:
            raise DuplicateWebhookError(
                idempotency_key=idempotency_key
            )

        # Step 8: Store idempotency key in Redis (1-hour TTL per FR-017)
        await self.redis_client.set_with_ttl(
            f"webhook:{idempotency_key}",
            "processed",
            3600  # 1 hour
        )

        # Step 9: Generate correlation ID and event ID
        correlation_id = str(uuid.uuid4())
        event_id = str(uuid.uuid4())

        # Step 10: Create WebhookEvent
        # Cast event_type to Literal type for type safety
        event_type_literal: Literal["issues.opened", "issues.labeled"] = event_type  # type: ignore

        webhook_event = WebhookEvent(
            event_id=event_id,
            event_type=event_type_literal,
            issue_number=issue_number,
            issue_title=issue_title,
            issue_body=issue_body,
            labels=labels,
            repository=repository,
            signature=signature,
            received_at=datetime.now(),
            correlation_id=correlation_id
        )

        return webhook_event
