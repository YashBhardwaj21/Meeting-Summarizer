"""Cleanup tasks for background execution."""

import logging
import uuid
from typing import Any
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
from app.services import storage_service
from app.models.enums import ChatStatus, JobStatus
from app.models.chat import Chat
from app.models.file import File
from app.models.job import ProcessingJob

logger = logging.getLogger(__name__)


async def cleanup_chat(ctx: dict[str, Any], chat_id_hex: str) -> None:
    """Asynchronously delete all data and files for a chat."""
    chat_id = uuid.UUID(chat_id_hex)
    logger.info(f"Starting cleanup for chat {chat_id}")
    
    async with async_session_factory() as db:
        try:
            # 1. Load relationships once
            chat_stmt = select(Chat).where(Chat.id == chat_id)
            chat = (await db.execute(chat_stmt)).scalar_one_or_none()
            if not chat:
                logger.warning(f"Chat {chat_id} not found during cleanup")
                return

            files_stmt = select(File).where(File.chat_id == chat_id)
            files = (await db.execute(files_stmt)).scalars().all()
            
            from app.models.meeting import Meeting
            meetings_stmt = select(Meeting).where(Meeting.chat_id == chat_id)
            meetings = (await db.execute(meetings_stmt)).scalars().all()
            
            jobs_stmt = (
                select(ProcessingJob)
                .join(File, ProcessingJob.file_id == File.id)
                .where(File.chat_id == chat_id)
            )
            jobs = (await db.execute(jobs_stmt)).scalars().all()

            # 2. Cancel any active jobs using job_service
            from app.services import job_service
            from app.utils.exceptions import InternalServerError
            
            active_jobs = [j for j in jobs if j.status in [JobStatus.QUEUED.value, JobStatus.PROCESSING.value]]
            for job in active_jobs:
                try:
                    await job_service.cancel_job(db, ctx["redis"], job.id)
                except InternalServerError as e:
                    # If abort fails, fail the whole cleanup. ARQ will retry.
                    logger.error(f"Cannot abort job {job.id}, failing cleanup: {e}")
                    raise
            
            # 3. Batch delete objects from storage ONLY AFTER jobs are cancelled
            storage_keys = [f.storage_key for f in files if f.storage_key]
            if storage_keys:
                logger.info(f"Deleting {len(storage_keys)} objects from storage for chat {chat_id}")
                storage_service.delete_objects(storage_keys)
            
            # 4. Mark chat and all children as fully deleted
            chat.status = ChatStatus.DELETED.value
            chat.deleted_at = datetime.now(timezone.utc)
            
            for f in files:
                f.deleted_at = chat.deleted_at
            for m in meetings:
                m.deleted_at = chat.deleted_at
            # ProcessingJob does not have deleted_at; it is implicitly soft-deleted
            
            await db.commit()
            logger.info(f"Successfully cleaned up chat {chat_id}")
            
        except Exception as exc:
            logger.error(f"Error during cleanup of chat {chat_id}: {exc}", exc_info=True)
            await db.rollback()
            raise


async def delete_file_job(ctx: dict[str, Any], storage_key: str) -> None:
    """Asynchronously delete a single file object from storage idempotently."""
    logger.info(f"Starting storage deletion for key {storage_key}")
    # storage_service.delete_object handles idempotency automatically for S3
    # (deleting a non-existent object succeeds)
    storage_service.delete_object(storage_key)
    logger.info(f"Successfully deleted object {storage_key}")
