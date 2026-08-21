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
            from app.models.enums import MeetingStatus
            meeting.status = MeetingStatus.CANCELLED.value
            
        await db.commit()
        
        # Abort the corresponding ARQ job
        try:
            aborted = await arq_pool.abort_job(job_id.hex)
            if not aborted:
                import logging
                logging.getLogger(__name__).warning(f"ARQ abort_job returned False for job {job_id.hex} (may not be running).")
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to abort ARQ job {job_id.hex}: {e}")
            from app.utils.exceptions import InternalServerError
            raise InternalServerError(f"Failed to abort job in queue: {e}")
            
    return job

async def claim_job(db: AsyncSession, job_id: uuid.UUID, attempt_count: int) -> ProcessingJob:
    """Atomically claim a queued job for processing."""
    from datetime import datetime, timezone
    from app.utils.exceptions import ConflictError
    
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise NotFoundError("Job not found.")
        
    if job.status == JobStatus.CANCELLED.value:
        raise ConflictError("Job is already cancelled.")
        
    if job.status != JobStatus.QUEUED.value:
        raise ConflictError(f"Cannot claim job. Current status is {job.status}")
        
    job.status = JobStatus.PROCESSING.value
    job.stage = "validation"
    job.started_at = datetime.now(timezone.utc)
    job.attempt_count = attempt_count
    
    await db.flush()
    return job

async def retry_job(db: AsyncSession, arq_pool, job_id: uuid.UUID) -> ProcessingJob:
    """Retry a failed or cancelled job."""
    from datetime import datetime, timezone
    from app.models.meeting import Meeting
    
    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id).with_for_update()
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise NotFoundError("Job not found.")
        
    if job.status not in [JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        from app.utils.exceptions import ConflictError
        raise ConflictError(f"Cannot retry job in status {job.status}")
        
    job.status = JobStatus.QUEUED.value
    job.stage = None
    job.error_code = None
    job.error_message = None
    job.completed_at = None
    job.started_at = None
    job.attempt_count = 0
    
    meeting = await db.scalar(select(Meeting).where(Meeting.id == job.meeting_id))
    if meeting:
        from app.models.enums import MeetingStatus
        meeting.status = MeetingStatus.PENDING.value
        
    await db.commit()
    await db.refresh(job)
    
    try:
        arq_job = await arq_pool.enqueue_job(
            "process_meeting_job",
            job_id=job_id.hex,
            _job_id=job_id.hex,
        )
        if not arq_job:
            raise RuntimeError("ARQ enqueue_job returned None (job not accepted by Redis).")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to enqueue retry for job {job_id}: {e}")
        job.status = JobStatus.FAILED.value
        job.error_code = "QUEUE_ENQUEUE_FAILED"
        job.error_message = str(e)
        if meeting:
            meeting.status = MeetingStatus.FAILED.value
        await db.commit()
        await db.refresh(job)
        from app.utils.exceptions import InternalServerError
        raise InternalServerError(f"Failed to enqueue processing job: {str(e)}")
        
    return job
