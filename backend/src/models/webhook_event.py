"""WebhookEvent pydantic model."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict


class WebhookEvent(BaseModel):
    """
    Represents a GitHub webhook event for issue creation or labeling.
    
    Attributes:
        event_id: Unique event identifier (UUID)
        event_type: Type of event (issues.opened or issues.labeled)
        issue_number: GitHub issue number
        issue_title: Issue title (max 256 characters)
        issue_body: Issue body content (truncated to 5000 characters)
        labels: List of issue labels (must contain 'generate-tests')
        repository: Repository full name (format: owner/repo)
        signature: HMAC-SHA256 signature (format: sha256=...)
        received_at: Timestamp when webhook was received
        correlation_id: Correlation ID for tracking (UUID)
    """
    
    model_config = ConfigDict(frozen=True)  # Immutable model
    
    event_id: str = Field(..., description="Unique event identifier (UUID)")
    event_type: Literal["issues.opened", "issues.labeled"] = Field(
        ...,
        description="GitHub event type"
    )
    issue_number: int = Field(..., gt=0, description="GitHub issue number")
    issue_title: str = Field(
        ...,
        max_length=256,
        description="Issue title (max 256 characters)"
    )
    issue_body: str = Field(
        ...,
        description="Issue body content (truncated to 5000 chars)"
    )
    labels: list[str] = Field(..., min_length=1, description="Issue labels")
    repository: str = Field(..., description="Repository name (owner/repo)")
    signature: str = Field(..., description="HMAC-SHA256 signature")
    received_at: datetime = Field(..., description="Webhook received timestamp")
    correlation_id: str = Field(..., description="Correlation ID (UUID)")
    
    @field_validator("issue_body")
    @classmethod
    def truncate_issue_body(cls, v: str) -> str:
        """Truncate issue body to 5000 characters."""
        if len(v) > 5000:
            return v[:5000]
        return v
    
    @field_validator("labels")
    @classmethod
    def validate_labels_contain_generate_tests(cls, v: list[str]) -> list[str]:
        """Validate that labels contain 'generate-tests' tag."""
        if "generate-tests" not in v:
            raise ValueError(
                "Labels must contain 'generate-tests' tag (FR-002)"
            )
        return v
    
    @field_validator("signature")
    @classmethod
    def validate_signature_format(cls, v: str) -> str:
        """Validate signature has 'sha256=' prefix."""
        if not v.startswith("sha256="):
            raise ValueError(
                "Signature must have 'sha256=' prefix for HMAC-SHA256 validation"
            )
        return v
    
    @field_validator("repository")
    @classmethod
    def validate_repository_format(cls, v: str) -> str:
        """Validate repository format is 'owner/repo'."""
        if "/" not in v or v.count("/") != 1:
            raise ValueError(
                "Repository must be in 'owner/repo' format"
            )
        owner, repo = v.split("/")
        if not owner or not repo:
            raise ValueError(
                "Repository owner and name cannot be empty"
            )
        return v
