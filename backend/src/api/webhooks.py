"""GitHub webhook endpoint for test case generation."""
import asyncio
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

import structlog
from fastapi import APIRouter, BackgroundTasks, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse

from src.models.webhook_event import WebhookEvent
from src.models.processing_job import ProcessingJob, JobStatus, WorkflowStage
from src.services.webhook_service import WebhookService
from src.services.ai_service import AIService
from src.core.exceptions import (
    InvalidWebhookSignatureError,
    InvalidWebhookPayloadError,
    DuplicateWebhookError
)

# Initialize structured logger
logger = structlog.get_logger(__name__)


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def process_webhook_background(
    webhook_event: WebhookEvent,
    job: ProcessingJob,
    ai_service: AIService,
    jobs_dict: dict
):
    """Background task to process webhook and generate test cases.
    
    This runs asynchronously after returning 202 to GitHub.
    
    Args:
        webhook_event: Validated webhook event
        job: Initial processing job
        ai_service: AIService instance for workflow execution
        jobs_dict: Dictionary to store job updates
    """
    log = logger.bind(
        job_id=job.job_id,
        correlation_id=job.correlation_id,
        issue_number=webhook_event.issue_number,
        repository=webhook_event.repository
    )
    
    try:
        log.info(
            "background_task_started",
            stage=job.current_stage.value
        )
        
        # Execute the full LangGraph workflow
        completed_job = await ai_service.execute_workflow(
            job=job,
            webhook_event=webhook_event
        )
        
        # Update job in storage
        jobs_dict[job.job_id] = completed_job
        
        log.info(
            "background_task_completed",
            status=completed_job.status.value,
            stage=completed_job.current_stage.value,
            duration_seconds=(completed_job.completed_at - completed_job.started_at).total_seconds() if completed_job.completed_at else None
        )
        
    except Exception as e:
        log.error(
            "background_task_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        # TODO: Update job status to FAILED


@router.post(
    "/github",
    status_code=status.HTTP_202_ACCEPTED,
    summary="GitHub Webhook Endpoint",
    description="Receives GitHub webhook events for issues with 'generate-tests' label"
)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery")
) -> JSONResponse:
    """Handle GitHub webhook for test case generation.
    
    This endpoint:
    1. Validates webhook signature (HMAC-SHA256)
    2. Checks for 'generate-tests' label
    3. Creates WebhookEvent and ProcessingJob
    4. Dispatches background task for AI workflow
    5. Returns 202 Accepted immediately
    
    Args:
        request: FastAPI request object
        background_tasks: Background task manager
        x_github_event: GitHub event type (e.g., "issues")
        x_hub_signature_256: HMAC-SHA256 signature
        x_github_delivery: Unique delivery ID
    
    Returns:
        JSONResponse with 202 status and correlation_id
    
    Raises:
        HTTPException 400: Invalid webhook format
        HTTPException 401: Invalid signature
        HTTPException 409: Duplicate webhook (idempotency)
        HTTPException 422: Missing 'generate-tests' label
    """
    # Get app state (services injected by main.py)
    webhook_service: WebhookService = request.app.state.webhook_service
    ai_service: AIService = request.app.state.ai_service
    
    log = logger.bind(
        event_type=x_github_event,
        delivery_id=x_github_delivery
    )
    
    log.info("webhook_received")
    
    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        log.error(
            "webhook_parse_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON payload: {str(e)}"
        )
    
    # Get raw body for signature validation
    body_bytes = await request.body()
    
    try:
        # Validate signature and parse event
        # Construct event type (e.g., "issues.opened")
        event_type_str = payload.get("action")
        if x_github_event == "issues" and event_type_str:
            full_event_type = f"issues.{event_type_str}"
        else:
            full_event_type = x_github_event
        
        webhook_event = await webhook_service.process_webhook(
            payload=body_bytes,
            signature=x_hub_signature_256,
            event_type=full_event_type
        )
        
    except InvalidWebhookSignatureError as e:
        log.warning(
            "webhook_signature_invalid",
            error_code=e.error_code
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": e.error_code,
                "message": str(e),
                "details": e.details
            }
        )
    
    except DuplicateWebhookError as e:
        idempotency_key = e.details.get("idempotency_key", "unknown")
        log.info(
            "webhook_duplicate_detected",
            error_code=e.error_code,
            idempotency_key=idempotency_key
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": e.error_code,
                "message": str(e),
                "details": e.details
            },
            headers={"X-Idempotency-Key": idempotency_key}
        )
    
    except InvalidWebhookPayloadError as e:
        # Missing 'generate-tests' label or other validation error
        log.warning(
            "webhook_payload_invalid",
            error_code=e.error_code,
            message=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": str(e),
                "details": e.details
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing error: {str(e)}"
        )
    
    # Create processing job
    correlation_id = str(uuid4())
    
    # Generate idempotency key from repository + issue number
    import hashlib
    key_string = f"{webhook_event.repository}-{webhook_event.issue_number}"
    idempotency_key = hashlib.sha256(key_string.encode('utf-8')).hexdigest()
    
    job = ProcessingJob(
        job_id=str(uuid4()),
        webhook_event_id=webhook_event.event_id,
        status=JobStatus.PENDING,
        started_at=datetime.now(),
        completed_at=None,
        error_message=None,
        error_code=None,
        retry_count=0,
        retry_delays=[5, 15, 45],
        last_retry_at=None,
        idempotency_key=idempotency_key,
        current_stage=WorkflowStage.RECEIVE,
        correlation_id=correlation_id
    )
    
    log = log.bind(
        job_id=job.job_id,
        correlation_id=correlation_id,
        issue_number=webhook_event.issue_number,
        repository=webhook_event.repository
    )
    
    log.info(
        "job_created",
        status=job.status.value,
        stage=job.current_stage.value
    )
    
    # Store initial job in app state
    request.app.state.jobs[job.job_id] = job
    
    # Dispatch background task
    background_tasks.add_task(
        process_webhook_background,
        webhook_event=webhook_event,
        job=job,
        ai_service=ai_service,
        jobs_dict=request.app.state.jobs
    )
    
    log.info(
        "webhook_accepted",
        status_code=202
    )
    
    # Return 202 Accepted immediately
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "accepted",
            "message": "Webhook received and queued for processing",
            "correlation_id": correlation_id,
            "job_id": job.job_id,
            "issue_number": webhook_event.issue_number,
            "repository": webhook_event.repository
        },
        headers={
            "X-Correlation-ID": correlation_id,
            "X-Job-ID": job.job_id
        }
    )


@router.get(
    "/health",
    summary="Webhook Health Check",
    description="Check if webhook endpoint is healthy"
)
async def webhook_health() -> Dict[str, Any]:
    """Health check for webhook endpoint.
    
    Returns:
        Dictionary with status and timestamp
    """
    return {
        "status": "healthy",
        "service": "webhooks",
        "timestamp": datetime.now().isoformat()
    }
