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
            # 1. Cancel any active jobs for this chat
            # (We find jobs via the meeting -> chat relationship, or just files -> chat)
            # Since files belong to chat, and jobs belong to files:
            jobs_stmt = (
                select(ProcessingJob)
                .join(File, ProcessingJob.file_id == File.id)
                .where(
                    File.chat_id == chat_id,
                    ProcessingJob.status.in_([JobStatus.QUEUED.value, JobStatus.PROCESSING.value])
                )
            )
            result = await db.execute(jobs_stmt)
            active_jobs = result.scalars().all()
            for job in active_jobs:
                job.status = JobStatus.CANCELLED.value
                logger.info(f"Cancelled job {job.id} for chat {chat_id}")
            
            # 2. Collect all storage keys
            files_stmt = select(File).where(File.chat_id == chat_id)
            result = await db.execute(files_stmt)
            files = result.scalars().all()
            
            storage_keys = [f.storage_key for f in files if f.storage_key]
            
            # 3. Batch delete objects from storage
            if storage_keys:
                logger.info(f"Deleting {len(storage_keys)} objects from storage for chat {chat_id}")
                storage_service.delete_objects(storage_keys)
            
            # 4. Mark chat as fully deleted
            # Note: SQLAlchemy cascade handles deleting the child rows (files, meetings, jobs)
            # when the chat is hard deleted. However, since we use soft deletes,
            # we just mark the chat as DELETED. 
            # In a true soft-delete system, we might also want to set deleted_at on children.
            # But the access pattern ensures that if a chat is deleted, its children are unreachable.
            
            chat_stmt = select(Chat).where(Chat.id == chat_id)
            result = await db.execute(chat_stmt)
            chat = result.scalar_one_or_none()
            
            if chat:
                chat.status = ChatStatus.DELETED.value
                chat.deleted_at = datetime.now(timezone.utc)
                
                # Also soft-delete children for consistency
                for f in files:
                    f.deleted_at = chat.deleted_at
                    
                await db.commit()
                logger.info(f"Successfully cleaned up chat {chat_id}")
            else:
                logger.warning(f"Chat {chat_id} not found during cleanup")
                
        except Exception as exc:
            logger.error(f"Error during cleanup of chat {chat_id}: {exc}", exc_info=True)
            await db.rollback()
            raise
