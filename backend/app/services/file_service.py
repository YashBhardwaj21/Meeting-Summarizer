"""File service — handles business logic for file uploads and management."""

import pathlib
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.file import File
from app.models.enums import MediaType, UploadStatus
from app.services import chat_service
from app.services import storage_service
from app.utils.exceptions import ConflictError, NotFoundError, ValidationError

settings = get_settings()

ALLOWED_AUDIO_MIMES = {
    "audio/mpeg", "audio/wav", "audio/x-wav", 
    "audio/mp4", "audio/ogg", "audio/webm", "audio/x-m4a"
}
ALLOWED_VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/webm", "video/x-matroska"
}
ALLOWED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mov", ".mkv"
}


def _validate_file_parameters(filename: str, content_type: str, size_bytes: int) -> MediaType:
    """Validate file metadata against allowed lists and size limits."""
    if size_bytes > settings.max_file_size_bytes:
        raise ValidationError(
            f"File exceeds maximum size of {settings.max_file_size_bytes} bytes.",
            error_code="FILE_TOO_LARGE"
        )

    ext = pathlib.Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File extension {ext} is not supported.",
            error_code="UNSUPPORTED_EXTENSION"
        )

    if content_type in ALLOWED_AUDIO_MIMES:
        return MediaType.AUDIO
    elif content_type in ALLOWED_VIDEO_MIMES:
        return MediaType.VIDEO
    else:
        raise ValidationError(
            f"MIME type {content_type} is not supported.",
            error_code="UNSUPPORTED_MIME_TYPE"
        )


async def request_presign(
    db: AsyncSession, 
    chat_id: uuid.UUID, 
    filename: str, 
    content_type: str, 
    size_bytes: int
) -> tuple[File, str]:
    """Validate upload intent, create pending File record, generate upload URL."""
    # 1. Verify chat exists and is active
    await chat_service.get_chat(db, chat_id)
    
    # 2. Validate file params
    media_type = _validate_file_parameters(filename, content_type, size_bytes)
    
    # 3. Create pending file record
    file_id = uuid.uuid4()
    storage_key = f"chats/{chat_id}/files/{file_id}/{filename}"
    
    file_record = File(
        id=file_id,
        chat_id=chat_id,
        filename=filename,
        mime_type=content_type,
        media_type=media_type.value,
        size_bytes=size_bytes,
        storage_key=storage_key,
        upload_status=UploadStatus.PENDING.value
    )
    db.add(file_record)
    await db.flush()
    
    # 4. Generate presigned URL
    url = storage_service.generate_presigned_upload_url(
        key=storage_key,
        content_type=content_type
    )
    
    return file_record, url


async def complete_upload(
    db: AsyncSession, 
    chat_id: uuid.UUID, 
    file_id: uuid.UUID
) -> File:
    """Verify object in storage and mark File as uploaded."""
    # 1. Get file and verify it belongs to this chat
    stmt = select(File).where(File.id == file_id, File.chat_id == chat_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise NotFoundError("File not found in this chat.")
        
    # 2. Check current status
    if file_record.upload_status == UploadStatus.UPLOADED.value:
        raise ConflictError("Upload is already completed.")
    if file_record.upload_status == UploadStatus.FAILED.value:
        raise ConflictError("Cannot complete a failed upload.")
        
    # 3. Verify object exists in storage
    exists = storage_service.check_object_exists(file_record.storage_key)
    if not exists:
        raise ValidationError(
            "File object not found in storage. Upload may not have finished.",
            error_code="OBJECT_NOT_FOUND"
        )
        
    # 4. Mark as completed
    file_record.upload_status = UploadStatus.UPLOADED.value
    file_record.completed_at = datetime.now(timezone.utc)
    await db.flush()
    
    return file_record


async def list_files(db: AsyncSession, chat_id: uuid.UUID) -> Sequence[File]:
    """List all files in a chat."""
    # Ensure chat exists
    await chat_service.get_chat(db, chat_id)
    
    stmt = select(File).where(File.chat_id == chat_id).order_by(File.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_file(db: AsyncSession, file_id: uuid.UUID) -> File:
    """Get a single file by ID."""
    stmt = select(File).where(File.id == file_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise NotFoundError("File not found.")
        
    return file_record


async def delete_file(db: AsyncSession, file_id: uuid.UUID) -> None:
    """Mark file as deleted.
    
    Storage cleanup happens asynchronously via worker.
    """
    file_record = await get_file(db, file_id)
    
    file_record.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    
    # TODO (Step 8/9): Enqueue cleanup job to remove from storage
