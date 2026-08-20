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
) -> ProcessingJob:
    """Update job status and progress (called by worker)."""
    job = await get_job(db, job_id)
    
    job.status = status.value
    if stage is not None:
        job.stage = stage
    if error_message is not None:
        job.error_message = error_message
        
    await db.flush()
    return job


async def cancel_job(db: AsyncSession, job_id: uuid.UUID) -> None:
    """Cancel a queued job."""
    job = await get_job(db, job_id)
    if job.status in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]:
        job.status = JobStatus.CANCELLED.value
        await db.flush()
