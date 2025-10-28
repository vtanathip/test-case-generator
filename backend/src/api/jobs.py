"""Jobs API endpoints for checking processing job status."""
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.models.processing_job import ProcessingJob

router = APIRouter()


@router.get(
    "/{job_id}",
    summary="Get Job Status",
    description="Retrieve the status of a test case generation job"
)
async def get_job_status(
    job_id: str,
    request: Request
) -> dict[str, Any]:
    """Get the status of a processing job.
    
    Args:
        job_id: Unique job identifier
        request: FastAPI request object
    
    Returns:
        Job status information
    
    Raises:
        HTTPException 404: Job not found
    """
    # Get jobs from app state
    jobs = getattr(request.app.state, 'jobs', {})

    if job_id not in jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )

    job: ProcessingJob = jobs[job_id]

    # Return job data (convert enums to strings)
    return {
        "job_id": job.job_id,
        "correlation_id": job.correlation_id,
        "webhook_event_id": job.webhook_event_id,
        "status": job.status.value,  # Convert enum to string
        "current_stage": job.current_stage.value,  # Convert enum to string
        "error_message": job.error_message,
        "error_code": job.error_code,
        "retry_count": job.retry_count,
        "started_at": job.started_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "last_retry_at": job.last_retry_at.isoformat() if job.last_retry_at else None
    }


@router.get(
    "/",
    summary="List Jobs",
    description="List all processing jobs (for debugging)"
)
async def list_jobs(request: Request) -> dict[str, Any]:
    """List all jobs in the system.
    
    Args:
        request: FastAPI request object
    
    Returns:
        List of job IDs and statuses
    """
    jobs = getattr(request.app.state, 'jobs', {})

    return {
        "count": len(jobs),
        "jobs": [
            {
                "job_id": job.job_id,
                "status": job.status.value,  # Convert enum to string
                "current_stage": job.current_stage.value,  # Convert enum to string
                "started_at": job.started_at.isoformat()
            }
            for job in jobs.values()
        ]
    }
