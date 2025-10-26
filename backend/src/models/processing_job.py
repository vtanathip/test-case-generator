"""ProcessingJob pydantic model."""
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class JobStatus(str, Enum):
    """Processing job status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowStage(str, Enum):
    """Workflow stages."""
    RECEIVE = "RECEIVE"
    RETRIEVE = "RETRIEVE"
    GENERATE = "GENERATE"
    COMMIT = "COMMIT"
    CREATE_PR = "CREATE_PR"
    FINALIZE = "FINALIZE"


class ProcessingJob(BaseModel):
    """
    Tracks the status of a test case generation workflow.
    
    Attributes:
        job_id: Unique job identifier (UUID)
        webhook_event_id: Reference to triggering webhook (UUID)
        status: Current job status (PENDING, PROCESSING, COMPLETED, FAILED, SKIPPED)
        started_at: Job start timestamp
        completed_at: Job completion timestamp (None until completed)
        error_message: Error details if failed (None if not failed)
        error_code: Error code from error-catalog.md (e.g., "E301", "E405")
        retry_count: Number of retry attempts (max 3)
        retry_delays: Exponential backoff delays in seconds (default [5, 15, 45])
        last_retry_at: Timestamp of most recent retry attempt
        idempotency_key: SHA256 hash for duplicate detection (64 characters)
        current_stage: Current workflow stage
        correlation_id: Shared correlation ID (UUID)
    """
    
    model_config = ConfigDict(frozen=True)  # Immutable model
    
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    webhook_event_id: str = Field(..., description="Triggering webhook event ID")
    status: JobStatus = Field(..., description="Current job status")
    started_at: datetime = Field(..., description="Job start timestamp")
    completed_at: Optional[datetime] = Field(
        None,
        description="Job completion timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error details if failed")
    error_code: Optional[str] = Field(None, description="Error code (E1xx-E5xx)")
    retry_count: int = Field(
        default=0,
        ge=0,
        le=3,
        description="Number of retry attempts (max 3)"
    )
    retry_delays: list[int] = Field(
        default=[5, 15, 45],
        description="Exponential backoff delays (seconds)"
    )
    last_retry_at: Optional[datetime] = Field(
        None,
        description="Most recent retry timestamp"
    )
    idempotency_key: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA256 hash (64 hex characters)"
    )
    current_stage: WorkflowStage = Field(..., description="Current workflow stage")
    correlation_id: str = Field(..., description="Correlation ID (UUID)")
    
    @field_validator("completed_at")
    @classmethod
    def validate_completed_at_after_started_at(
        cls,
        v: Optional[datetime],
        info
    ) -> Optional[datetime]:
        """Validate completed_at is after started_at."""
        if v is not None:
            started_at = info.data.get("started_at")
            if started_at and v <= started_at:
                raise ValueError(
                    "completed_at must be after started_at"
                )
        return v
    
    @field_validator("error_message")
    @classmethod
    def validate_error_message_for_failed_status(
        cls,
        v: Optional[str],
        info
    ) -> Optional[str]:
        """Validate error_message is provided when status is FAILED."""
        status = info.data.get("status")
        if status == JobStatus.FAILED and not v:
            raise ValueError(
                "error_message is required when status is FAILED"
            )
        return v
