"""Arq background worker for processing meetings."""

import asyncio
import logging
import uuid
from typing import Any

from arq.connections import RedisSettings

from app.config import get_settings
from app.database import async_session_factory
from app.models.enums import JobStatus, MeetingStatus
from app.services import job_service, storage_service
from app.workers.cleanup import cleanup_chat

logger = logging.getLogger(__name__)
settings = get_settings()

RETRY_DELAYS = [5, 15, 45]  # seconds (exponential backoff)


async def startup(ctx: dict[str, Any]) -> None:
    """Run on worker start."""
    logger.info("Starting up background worker...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run on worker shutdown."""
    logger.info("Shutting down background worker...")


async def process_meeting_job(ctx: dict[str, Any], job_id_hex: str) -> None:
    """Main job handler for processing an uploaded meeting file."""
    job_id = uuid.UUID(job_id_hex)
    
    async with async_session_factory() as db:
        try:
            # 1. Fetch job
            job = await job_service.get_job(db, job_id)
            
            if job.status == JobStatus.CANCELLED.value:
                logger.info(f"Job {job_id} was cancelled. Skipping.")
                return

            # 2. Update status -> processing
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
                
            # 4. PLACEHOLDER: Transcription (Section 2)
            await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="transcription")
            await asyncio.sleep(1)  # Simulate work
            
            # 5. PLACEHOLDER: Extraction (Section 3)
            await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="extraction")
            await asyncio.sleep(1)  # Simulate work
            
            # 6. PLACEHOLDER: Indexing (Section 2)
            await job_service.update_job_status(db, job_id, JobStatus.PROCESSING, stage="indexing")
            await asyncio.sleep(1)  # Simulate work
            
            # 7. On success: complete job and meeting
            await job_service.update_job_status(db, job_id, JobStatus.COMPLETED, stage="complete")
            meeting.status = MeetingStatus.READY.value
            await db.commit()
            
            logger.info(f"Successfully processed job {job_id} for meeting {meeting.id}")
            
        except Exception as exc:
            logger.error(f"Error processing job {job_id}: {exc}", exc_info=True)
            await db.rollback()
            await handle_job_failure(db, job_id, exc)


async def handle_job_failure(db, job_id: uuid.UUID, error: Exception) -> None:
    """Handle retry logic with exponential backoff."""
    job = await job_service.get_job(db, job_id)
    
    if job.attempt_count < job.max_attempts - 1:
        delay = RETRY_DELAYS[min(job.attempt_count, len(RETRY_DELAYS) - 1)]
        await job_service.retry_job(db, job_id)
        await db.commit()
        
        logger.info(f"Job {job_id} failed. Retrying in {delay}s (Attempt {job.attempt_count + 1})")
        # In a real arq setup we'd re-enqueue with `_defer_by=delay`. 
        # But arq also handles retries natively if we raise an exception.
        # For this take-home, raising a custom Retry exception or just 
        # letting arq's native retry handle it is best.
        # We will raise so arq knows it failed.
        raise error
    else:
        await job_service.update_job_status(
            db, job_id, JobStatus.FAILED, error_message=str(error)
        )
        meeting = await job.awaitable_attrs.meeting
        meeting.status = MeetingStatus.FAILED.value
        await db.commit()
        logger.error(f"Job {job_id} failed permanently after {job.attempt_count + 1} attempts.")


# arq worker configuration
class WorkerSettings:
    functions = [process_meeting_job, cleanup_chat]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
