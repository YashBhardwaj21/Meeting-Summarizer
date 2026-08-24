"""Arq background worker for processing meetings."""

import asyncio
import logging
import uuid
from typing import Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from arq.worker import Retry
from arq.connections import RedisSettings

from app.config import get_settings
from app.database import async_session_factory
from app.models.enums import JobStatus, MeetingStatus
from app.models.meeting import Meeting
from app.models.file import File
from app.models.job import ProcessingJob
from sqlalchemy import select
from app.services import job_service, storage_service
from app.workers.cleanup import cleanup_chat, delete_file_job
from app.workers.transcription import run_transcription_pipeline
from app.utils.exceptions import RetryableProcessingError, PermanentProcessingError

logger = logging.getLogger(__name__)
settings = get_settings()

RETRY_DELAYS = [5, 15, 45]  # seconds (exponential backoff)


async def startup(ctx: dict[str, Any]) -> None:
    """Run on worker start."""
    logger.info("Starting up background worker...")
    from app.workers.worker import WorkerSettings
    logger.info(f"Registered functions: {[f.__name__ for f in WorkerSettings.functions]}")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run on worker shutdown."""
    logger.info("Shutting down background worker...")


async def _check_cancelled(db: AsyncSession, job_id: uuid.UUID) -> bool:
    """Check if the job has been cancelled. Returns True if cancelled."""
    job = await job_service.get_job(db, job_id)
    return job.status == JobStatus.CANCELLED.value


async def process_meeting_job(ctx: dict[str, Any], job_id_hex: str) -> None:
    """Main job handler for processing an uploaded meeting file."""
    logger.info(f"[WORKER] received {job_id_hex}")
    job_id = uuid.UUID(job_id_hex)
    job_try = ctx.get("job_try", 1)
    
    async with async_session_factory() as db:
        try:
            from app.utils.exceptions import ConflictError, NotFoundError
            
            try:
                job = await job_service.claim_job(db, job_id, job_try)
                await db.commit()
                logger.info(f"[WORKER] claimed {job_id}")
            except NotFoundError:
                logger.info(f"Job {job_id} not found. Skipping.")
                return
            except ConflictError as e:
                logger.info(f"Failed to claim job {job_id}: {e}")
                return
            
            # Fetch related meeting and file
            meeting = await db.scalar(select(Meeting).where(Meeting.id == job.meeting_id))
            file_record = await db.scalar(select(File).where(File.id == job.file_id))
            
            if not meeting or not file_record:
                raise PermanentProcessingError(
                    "Meeting or File not found for job.",
                    error_code="DATA_NOT_FOUND"
                )
            
            # 3. Validate file exists in storage
            exists = storage_service.check_object_exists(file_record.storage_key)
            if not exists:
                raise PermanentProcessingError(
                    "File object not found in storage.",
                    error_code="MEDIA_NOT_FOUND"
                )
                
            # Execute the real pipeline
            metrics = {}
            await run_transcription_pipeline(db, job, meeting, file_record, metrics)
            
            # On success: update metrics and complete job
            try:
                # Reload job to ensure we don't overwrite CANCELLED
                current_job = await job_service.get_job(db, job_id)
                if current_job.status != JobStatus.CANCELLED.value:
                    await job_service.update_job_status(db, job_id, JobStatus.COMPLETED, stage="complete", processing_metrics=metrics)
                    await db.commit()
                    logger.info(f"[WORKER] COMPLETED {job_id}")
                else:
                    logger.info(f"[WORKER] Job {job_id} was cancelled, skipping COMPLETED state")
            except Exception as e:
                logger.warning(f"[WORKER] Failed to complete job {job_id}, it might have been cancelled: {e}")
                await db.rollback()
            
        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} cancelled during processing.")
            await db.rollback()
            try:
                # Reload and attempt to finalize CANCELLED state
                job = await job_service.get_job(db, job_id)
                if job.status != JobStatus.CANCELLED.value:
                    await job_service.update_job_status(db, job_id, JobStatus.CANCELLED)
                    await db.commit()
            except Exception as e:
                logger.warning(f"Could not finalize cancel state for {job_id}: {e}")
                await db.rollback()
            # Do not re-raise CancelledError to prevent ARQ from treating it as a worker crash
            return
        except RetryableProcessingError as exc:
            logger.warning(f"Transient error processing job {job_id}: {exc}")
            await db.rollback()
            await handle_job_failure(db, job_id, exc, job_try)
        except PermanentProcessingError as exc:
            logger.error(f"Permanent error processing job {job_id}: {exc}")
            await db.rollback()
            # Force attempt count to max_attempts so it fails immediately
            await handle_job_failure(db, job_id, exc, job.max_attempts)
        except Exception as exc:
            await db.rollback()
            # If the job was already cancelled by the user, we might get a ConflictError here 
            # when trying to complete it or due to other concurrent modifications.
            # We don't want to override CANCELLED with FAILED.
            job = await job_service.get_job(db, job_id)
            if job.status == JobStatus.CANCELLED.value:
                logger.warning(f"Job {job_id} raised an error but is already cancelled. Ignoring.")
                return
                
            logger.error(f"Unexpected error processing job {job_id}: {exc}", exc_info=True)
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
        await db.commit()
        logger.error(f"Job {job_id} failed permanently after {job_try} attempts.")


async def check_stale_jobs(ctx: dict[str, Any]) -> None:
    """Cron task to fail stale jobs."""
    async with async_session_factory() as db:
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import update
        now = datetime.now(timezone.utc)
        
        # QUEUE_TIMEOUT: 5 minutes
        queue_timeout = now - timedelta(minutes=5)
        stmt_queued = (
            select(ProcessingJob)
            .where(
                ProcessingJob.status == JobStatus.QUEUED.value,
                ProcessingJob.created_at < queue_timeout
            )
        )
        result_q = await db.execute(stmt_queued)
        
        from arq.jobs import Job as ArqJob, JobStatus as ArqJobStatus
        arq_pool = ctx["redis"]
        
        for job in result_q.scalars().all():
            arq_job = ArqJob(job.id.hex, arq_pool)
            try:
                status = await arq_job.status()
                
                if status == ArqJobStatus.not_found:
                    logger.warning(f"Job {job.id.hex} QUEUED but not found in ARQ. Re-enqueuing.")
                    try:
                        await arq_pool.enqueue_job(
                            "process_meeting_job",
                            job_id_hex=job.id.hex,
                            _job_id=job.id.hex,
                        )
                    except Exception as e:
                        logger.error(f"Failed to re-enqueue {job.id.hex}, failing job: {e}")
                        await job_service.update_job_status(
                            db, job.id, JobStatus.FAILED, 
                            error_code="QUEUE_ENQUEUE_FAILED", 
                            error_message="Job vanished from queue and re-enqueue failed."
                        )
                elif status == ArqJobStatus.complete:
                    logger.warning(f"Job {job.id.hex} is complete in ARQ but QUEUED in DB. Reconciling.")
                    await job_service.update_job_status(db, job.id, JobStatus.COMPLETED)
                elif status == ArqJobStatus.aborted:
                    logger.warning(f"Job {job.id.hex} aborted in ARQ. Marking FAILED.")
                    await job_service.update_job_status(
                        db, job.id, JobStatus.FAILED, 
                        error_code="QUEUE_TIMEOUT", 
                        error_message="Job aborted or disappeared from ARQ"
                    )
            except Exception as e:
                logger.error(f"Error checking ARQ status for {job.id.hex}: {e}")

        # PROCESSING_TIMEOUT
        processing_timeout = now - timedelta(seconds=settings.processing_job_timeout_seconds)
        stmt_proc = (
            select(ProcessingJob)
            .where(
                ProcessingJob.status == JobStatus.PROCESSING.value,
                ProcessingJob.started_at < processing_timeout
            )
        )
        result_p = await db.execute(stmt_proc)
        for job in result_p.scalars().all():
            await job_service.update_job_status(
                db, 
                job.id, 
                JobStatus.FAILED, 
                error_code="PROCESSING_TIMEOUT", 
                error_message="Job exceeded processing timeout"
            )
            try:
                await ctx["redis"].abort_job(job.id.hex)
            except Exception as e:
                logger.error(f"Failed to abort stale ARQ job {job.id.hex}: {e}")
                
        await db.commit()


# arq worker configuration
class WorkerSettings:
    functions = [process_meeting_job, cleanup_chat, delete_file_job]
    from arq.cron import cron
    cron_jobs = [cron(check_stale_jobs, minute=set(range(0, 60, 5)))]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 1
    allow_abort_jobs = True
    job_timeout = settings.processing_job_timeout_seconds
