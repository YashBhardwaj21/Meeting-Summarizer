"""Arq background worker for processing meetings."""

import asyncio
import logging
import uuid
from typing import Any

from arq.worker import Retry
from arq.connections import RedisSettings

from app.config import get_settings
from app.database import async_session_factory
from app.models.enums import JobStatus, MeetingStatus
from app.services import job_service, storage_service
from app.workers.cleanup import cleanup_chat, delete_file_job

logger = logging.getLogger(__name__)
settings = get_settings()

RETRY_DELAYS = [5, 15, 45]  # seconds (exponential backoff)


async def startup(ctx: dict[str, Any]) -> None:
    """Run on worker start."""
    logger.info("Starting up background worker...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run on worker shutdown."""
    logger.info("Shutting down background worker...")


async def _check_cancelled(db: AsyncSession, job_id: uuid.UUID) -> bool:
    """Check if the job has been cancelled. Returns True if cancelled."""
    job = await job_service.get_job(db, job_id)
    return job.status == JobStatus.CANCELLED.value


async def process_meeting_job(ctx: dict[str, Any], job_id_hex: str) -> None:
    """Main job handler for processing an uploaded meeting file."""
    job_id = uuid.UUID(job_id_hex)
    job_try = ctx.get("job_try", 1)
    
    async with async_session_factory() as db:
        try:
            # 1. Fetch job
            job = await job_service.get_job(db, job_id)
            
            if job.status == JobStatus.CANCELLED.value:
                logger.info(f"Job {job_id} was cancelled. Skipping.")
                return

            # 2. Update status -> processing, sync attempt count
            job.attempt_count = job_try
            await job_service.update_job_status(
                db, job_id, JobStatus.PROCESSING, stage="validation"
            )
            
            # Fetch related meeting and file
            meeting = await job.awaitable_attrs.meeting
            file_record = await meeting.awaitable_attrs.file
            
            # 3. Validate file exists in storage
            exists = storage_service.check_object_exists(file_record.storage_key)
            if not exists:
                raise Exception("File object not found in storage.")
                
            # 3. Transcription stage (placeholder)
            if await _check_cancelled(db, job_id):
                logger.info(f"Job {job_id} cancelled before transcription.")
                return
                
            await job_service.update_job_status(
                db, job_id, JobStatus.PROCESSING, stage="transcription"
            )
            await asyncio.sleep(2)  # Simulate transcription work
            
            # 4. Extraction stage (placeholder)
            if await _check_cancelled(db, job_id):
                logger.info(f"Job {job_id} cancelled before extraction.")
                return
                
            await job_service.update_job_status(
                db, job_id, JobStatus.PROCESSING, stage="extraction"
            )
            await asyncio.sleep(2)  # Simulate LLM extraction work
            
            # 5. Indexing stage (placeholder)
            if await _check_cancelled(db, job_id):
                logger.info(f"Job {job_id} cancelled before indexing.")
                return
                
            await job_service.update_job_status(
                db, job_id, JobStatus.PROCESSING, stage="indexing"
            )
            await asyncio.sleep(1)  # Simulate work
            
            # 7. On success: complete job and meeting
            await job_service.update_job_status(db, job_id, JobStatus.COMPLETED, stage="complete")
            meeting.status = MeetingStatus.READY.value
            await db.commit()
            
            logger.info(f"Successfully processed job {job_id} for meeting {meeting.id}")
            
        except Exception as exc:
            logger.error(f"Error processing job {job_id}: {exc}", exc_info=True)
            await db.rollback()
            await handle_job_failure(db, job_id, exc, job_try)


async def handle_job_failure(db, job_id: uuid.UUID, error: Exception, job_try: int) -> None:
    """Handle retry logic with exponential backoff via arq.Retry."""
    job = await job_service.get_job(db, job_id)
    
    if job_try < job.max_attempts:
        delay = RETRY_DELAYS[min(job_try - 1, len(RETRY_DELAYS) - 1)]
        
        # Mark as QUEUED for the retry
        await job_service.update_job_status(db, job_id, JobStatus.QUEUED)
        await db.commit()
        
        logger.info(f"Job {job_id} failed. Retrying in {delay}s (Attempt {job_try + 1})")
        raise Retry(defer=delay)
    else:
        await job_service.update_job_status(
            db, job_id, JobStatus.FAILED, error_message=str(error)
        )
        meeting = await job.awaitable_attrs.meeting
        meeting.status = MeetingStatus.FAILED.value
        await db.commit()
        logger.error(f"Job {job_id} failed permanently after {job_try} attempts.")


# arq worker configuration
class WorkerSettings:
    functions = [process_meeting_job, cleanup_chat, delete_file_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
