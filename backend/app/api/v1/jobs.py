"""Job API routes."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.job import JobResponse
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/meeting/{meeting_id}",
    response_model=JobResponse,
    summary="Get active job by meeting ID",
)
async def get_job_by_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the most relevant background job for a meeting."""
    return await job_service.get_latest_job_for_meeting(db, meeting_id)

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
)
async def get_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the real-time processing status and stage of a background job."""
    return await job_service.get_job(db, job_id)

@router.post(
    "/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel a running job",
)
async def cancel_job_endpoint(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cancel an active or queued processing job."""
    from app.models.enums import JobStatus
    from fastapi import HTTPException
    
    # 1. Fetch job to check state
    try:
        job = await job_service.get_job(db, job_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    # 2. Prevent cancellation if already finished
    if job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        raise HTTPException(status_code=409, detail=f"Job is already {job.status}.")
        
    # 3. Perform atomic cancellation
    arq_pool = request.app.state.arq_pool
    cancelled_job = await job_service.cancel_job(db, arq_pool, job_id)
    return cancelled_job

@router.post(
    "/{job_id}/retry",
    response_model=JobResponse,
    summary="Retry a failed or cancelled job",
)
async def retry_job_endpoint(
    job_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed or cancelled processing job."""
    from fastapi import HTTPException
    
    arq_pool = request.app.state.arq_pool
    try:
        from app.utils.exceptions import ConflictError
        retried_job = await job_service.retry_job(db, arq_pool, job_id)
        return retried_job
    except job_service.NotFoundError:
        raise HTTPException(status_code=404, detail="Job not found.")
    except Exception as e:
        if e.__class__.__name__ == "ConflictError":
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
