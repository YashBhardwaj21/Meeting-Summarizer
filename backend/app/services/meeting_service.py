"""Meeting service — handles creation of meetings and job enqueuing."""

import uuid

from arq.connections import ArqRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.job import ProcessingJob
from app.models.enums import MeetingStatus, UploadStatus, JobStatus
from app.services import chat_service
from app.services import file_service
from app.utils.exceptions import ConflictError


async def create_meeting(
    db: AsyncSession, 
    arq_pool: ArqRedis,
    chat_id: uuid.UUID, 
    file_id: uuid.UUID
) -> tuple[Meeting, ProcessingJob]:
    """Creates a meeting from an uploaded file and enqueues a processing job."""
    
    # 1. Verify chat is active
    await chat_service.get_chat(db, chat_id)
    
    # 2. Verify file exists and is fully uploaded
    file_record = await file_service.get_file(db, file_id)
    if file_record.chat_id != chat_id:
        raise ConflictError("File does not belong to this chat.")
    if file_record.upload_status != UploadStatus.UPLOADED.value:
        raise ConflictError("File is not fully uploaded yet.")
        
    # 3. Idempotency check: does a meeting already exist for this file?
    stmt = select(Meeting).where(Meeting.file_id == file_id)
    result = await db.execute(stmt)
    existing_meeting = result.scalar_one_or_none()
    
    if existing_meeting:
        # Fetch the associated job
        job_stmt = select(ProcessingJob).where(ProcessingJob.meeting_id == existing_meeting.id)
        job_result = await db.execute(job_stmt)
        existing_job = job_result.scalar_one()
        return existing_meeting, existing_job

    # 4. Create new Meeting
    meeting_id = uuid.uuid4()
    meeting = Meeting(
        id=meeting_id,
        chat_id=chat_id,
        file_id=file_id,
        status=MeetingStatus.PENDING.value
    )
    db.add(meeting)
    
    # 5. Create new Job
    job_id = uuid.uuid4()
    job = ProcessingJob(
        id=job_id,
        file_id=file_id,
        meeting_id=meeting_id,
        status=JobStatus.QUEUED.value
    )
    db.add(job)
    await db.commit()
    
    # 6. Enqueue job to Redis via arq
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        arq_job = await arq_pool.enqueue_job(
            "process_meeting_job",
            job_id=job_id.hex,
            _job_id=job_id.hex,
        )
        logger.info(f"Successfully enqueued ARQ job. DB Job ID: {job_id} | ARQ Job accepted (new): {arq_job is not None}")
    except Exception as e:
        logger.error(f"Failed to enqueue job {job_id}: {e}")
        
        from app.services.job_service import update_job_status
        await update_job_status(db, job_id, JobStatus.FAILED, error_code="QUEUE_ENQUEUE_FAILED", error_message=str(e))
        await db.commit()
        await db.refresh(job)
        await db.refresh(meeting)
        
        from app.utils.exceptions import InternalServerError
        raise InternalServerError(f"Failed to enqueue processing job: {str(e)}")
        
    return meeting, job


async def get_meeting(db: AsyncSession, meeting_id: uuid.UUID) -> Meeting:
    """Get a meeting by ID."""
    stmt = select(Meeting).where(Meeting.id == meeting_id)
    result = await db.execute(stmt)
    meeting = result.scalar_one_or_none()
    
    if not meeting:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("Meeting not found.")
        
    return meeting


async def list_meetings(db: AsyncSession, chat_id: uuid.UUID) -> list[Meeting]:
    """List all meetings in a chat."""
    # Ensure chat exists and is active
    await chat_service.get_chat(db, chat_id)
    
    stmt = select(Meeting).where(
        Meeting.chat_id == chat_id,
        Meeting.deleted_at.is_(None)
    ).order_by(Meeting.created_at.desc())
    
    result = await db.execute(stmt)
    return list(result.scalars().all())
