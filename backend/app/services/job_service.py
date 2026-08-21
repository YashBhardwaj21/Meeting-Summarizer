"""Job service — handles job tracking and retries."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ProcessingJob
from app.models.enums import JobStatus
from app.utils.exceptions import NotFoundError


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> ProcessingJob:
    """Retrieve a job by ID."""
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise NotFoundError("Job not found.")
        
    return job


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: JobStatus,
    stage: str | None = None,
    error_message: str | None = None,
    expected_status: JobStatus | None = None,
) -> ProcessingJob:
    """Update job status and progress (called by worker)."""
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise NotFoundError("Job not found.")
        
    if expected_status and job.status != expected_status.value:
        from app.utils.exceptions import ConflictError
        raise ConflictError(f"Job status is {job.status}, expected {expected_status.value}")
    
    job.status = status.value
    if stage is not None:
        job.stage = stage
    if error_message is not None:
        job.error_message = error_message
        
    await db.flush()
    return job


async def cancel_job(db: AsyncSession, arq_pool, job_id: uuid.UUID) -> ProcessingJob:
    """Cancel a queued or processing job."""
    from datetime import datetime, timezone
    from app.models.meeting import Meeting
    
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise NotFoundError("Job not found.")
        
    if job.status in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]:
        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.now(timezone.utc)
        
        meeting = await db.scalar(select(Meeting).where(Meeting.id == job.meeting_id))
        if meeting:
            meeting.status = "CANCELLED"
            
        await db.commit()
        
        # Abort the corresponding ARQ job
        try:
            await arq_pool.abort_job(job_id.hex)
        except Exception:
            pass
            
    return job
