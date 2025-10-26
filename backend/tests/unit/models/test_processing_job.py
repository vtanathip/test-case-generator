"""Unit tests for ProcessingJob model."""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.models.processing_job import ProcessingJob, JobStatus, WorkflowStage

# Valid 64-character idempotency key (SHA256 hex format) for test fixtures
VALID_IDEMPOTENCY_KEY = "abc123def456abc123def456abc123def456abc123def456abc123def456abcd"


class TestProcessingJobValidation:
    """Test ProcessingJob model validation rules."""

    def test_create_valid_processing_job(self):
        """Test creating a valid processing job."""
        started_at = datetime.now()
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=started_at,
            completed_at=None,
            error_message=None,
            error_code=None,
            retry_count=0,
            retry_delays=[5, 15, 45],
            last_retry_at=None,
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert job.job_id == "770e8400-e29b-41d4-a716-446655440000"
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert job.retry_delays == [5, 15, 45]
        assert job.current_stage == WorkflowStage.RECEIVE

    def test_status_enum_validation(self):
        """Test status must be one of valid JobStatus enum values."""
        # Valid statuses
        valid_statuses = [
            JobStatus.PENDING,
            JobStatus.PROCESSING,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.SKIPPED
        ]
        
        for status in valid_statuses:
            job = ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=status,
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.RECEIVE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
            assert job.status == status
        
        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status="INVALID_STATUS",
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.RECEIVE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "status" in str(exc_info.value)

    def test_stage_enum_validation(self):
        """Test current_stage must be one of valid WorkflowStage enum values."""
        # Valid stages (6-stage workflow from data-model.md)
        valid_stages = [
            WorkflowStage.RECEIVE,
            WorkflowStage.RETRIEVE,
            WorkflowStage.GENERATE,
            WorkflowStage.COMMIT,
            WorkflowStage.CREATE_PR,
            WorkflowStage.FINALIZE
        ]
        
        for stage in valid_stages:
            job = ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.PENDING,
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=stage,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
            assert job.current_stage == stage
        
        # Invalid stage
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.PENDING,
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage="INVALID_STAGE",
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "current_stage" in str(exc_info.value)

    def test_retry_count_max_validation(self):
        """Test retry_count must not exceed 3 (per FR-011 exponential backoff)."""
        # Valid retry counts (0-3)
        for count in [0, 1, 2, 3]:
            job = ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.PROCESSING,
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.GENERATE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001",
                retry_count=count
            )
            assert job.retry_count == count
        
        # Invalid retry count (exceeds max 3)
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.PROCESSING,
                started_at=datetime.now(),
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.GENERATE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001",
                retry_count=4
            )
        assert "retry_count" in str(exc_info.value)

    def test_retry_delays_default(self):
        """Test retry_delays defaults to [5, 15, 45] (exponential backoff per FR-011)."""
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=datetime.now(),
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        assert job.retry_delays == [5, 15, 45]

    def test_completed_at_after_started_at(self):
        """Test completed_at must be after started_at."""
        started_at = datetime.now()
        valid_completed_at = started_at + timedelta(seconds=30)
        invalid_completed_at = started_at - timedelta(seconds=10)
        
        # Valid: completed_at after started_at
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.COMPLETED,
            started_at=started_at,
            completed_at=valid_completed_at,
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.FINALIZE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert job.completed_at > job.started_at
        
        # Invalid: completed_at before started_at
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.COMPLETED,
                started_at=started_at,
                completed_at=invalid_completed_at,
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.FINALIZE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "completed_at" in str(exc_info.value)

    def test_error_message_required_for_failed_status(self):
        """Test error_message is required when status is FAILED."""
        # Valid: FAILED status with error_message and error_code
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.FAILED,
            started_at=datetime.now(),
            error_message="AI generation timeout after 120 seconds",
            error_code="E302",
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.GENERATE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert job.error_message == "AI generation timeout after 120 seconds"
        assert job.error_code == "E302"
        
        # Invalid: FAILED status without error_message
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.FAILED,
                started_at=datetime.now(),
                error_message=None,
                error_code=None,
                idempotency_key=VALID_IDEMPOTENCY_KEY,
                current_stage=WorkflowStage.GENERATE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "error_message" in str(exc_info.value)

    def test_state_machine_transitions(self):
        """Test valid state machine transitions for ProcessingJob status."""
        # Valid transitions:
        # PENDING → PROCESSING
        # PROCESSING → COMPLETED
        # PROCESSING → FAILED
        # PENDING → SKIPPED
        
        # PENDING → PROCESSING
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=datetime.now(),
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert job.status == JobStatus.PENDING
        
        # Simulate transition to PROCESSING (in real implementation, this would use a method)
        job_processing = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.PROCESSING,
            started_at=job.started_at,
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.RETRIEVE,
            correlation_id=job.correlation_id
        )
        assert job_processing.status == JobStatus.PROCESSING
        
        # PROCESSING → COMPLETED
        job_completed = ProcessingJob(
            job_id=job.job_id,
            webhook_event_id=job.webhook_event_id,
            status=JobStatus.COMPLETED,
            started_at=job.started_at,
            completed_at=datetime.now() + timedelta(seconds=30),
            idempotency_key=job.idempotency_key,
            current_stage=WorkflowStage.FINALIZE,
            correlation_id=job.correlation_id
        )
        assert job_completed.status == JobStatus.COMPLETED
        
        # Invalid transition: COMPLETED → PROCESSING (would require validation in model)
        # This test verifies the model accepts the values, but business logic should prevent this

    def test_idempotency_key_format(self):
        """Test idempotency_key is SHA256 hash format (per FR-017)."""
        # Valid SHA256 hash (64 hex characters)
        valid_key = "a" * 64
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=datetime.now(),
            idempotency_key=valid_key,
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert len(job.idempotency_key) == 64
        
        # Invalid: Too short for SHA256
        with pytest.raises(ValidationError) as exc_info:
            ProcessingJob(
                job_id="770e8400-e29b-41d4-a716-446655440000",
                webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
                status=JobStatus.PENDING,
                started_at=datetime.now(),
                idempotency_key="short",
                current_stage=WorkflowStage.RECEIVE,
                correlation_id="660e8400-e29b-41d4-a716-446655440001"
            )
        assert "idempotency_key" in str(exc_info.value)

    def test_processing_job_immutability(self):
        """Test ProcessingJob is immutable once created (frozen model)."""
        job = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PENDING,
            started_at=datetime.now(),
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.RECEIVE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        
        # Attempt to modify status should fail
        with pytest.raises(ValidationError):
            job.status = JobStatus.COMPLETED

    def test_last_retry_at_tracking(self):
        """Test last_retry_at updates with each retry attempt."""
        started_at = datetime.now()
        first_retry = started_at + timedelta(seconds=5)
        second_retry = started_at + timedelta(seconds=20)  # 5 + 15
        
        # First retry
        job_retry1 = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PROCESSING,
            started_at=started_at,
            retry_count=1,
            last_retry_at=first_retry,
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.GENERATE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert job_retry1.retry_count == 1
        assert job_retry1.last_retry_at == first_retry
        
        # Second retry
        job_retry2 = ProcessingJob(
            job_id="770e8400-e29b-41d4-a716-446655440000",
            webhook_event_id="550e8400-e29b-41d4-a716-446655440000",
            status=JobStatus.PROCESSING,
            started_at=started_at,
            retry_count=2,
            last_retry_at=second_retry,
            idempotency_key=VALID_IDEMPOTENCY_KEY,
            current_stage=WorkflowStage.GENERATE,
            correlation_id="660e8400-e29b-41d4-a716-446655440001"
        )
        assert job_retry2.retry_count == 2
        assert job_retry2.last_retry_at == second_retry
        assert job_retry2.last_retry_at > job_retry1.last_retry_at

