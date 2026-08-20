"""File API routes."""

import uuid

from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.file import FileResponse, PresignRequest, PresignResponse
from app.services import file_service

router = APIRouter(tags=["files"])
settings = get_settings()


@router.post(
    "/chats/{chat_id}/uploads/presign",
    response_model=PresignResponse,
    summary="Request a presigned URL for direct upload",
)
async def request_presign_endpoint(
    chat_id: uuid.UUID,
    request: PresignRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiates the upload process. Validates the file extension, MIME type, 
    and size. Returns a presigned URL that the browser can use to upload 
    directly to MinIO/R2 without passing through the backend.
    """
    file_record, upload_url = await file_service.request_presign(
        db,
        chat_id=chat_id,
        filename=request.filename,
        content_type=request.content_type,
        size_bytes=request.size_bytes,
    )
    
    return PresignResponse(
        file_id=file_record.id,
        upload_url=upload_url,
        expires_in=settings.presign_expiry_seconds,
    )


@router.post(
    "/chats/{chat_id}/files/{file_id}/complete",
    response_model=FileResponse,
    summary="Confirm an upload is complete",
)
async def complete_upload_endpoint(
    chat_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the client after they successfully upload the file to the 
    presigned URL. Verifies the object exists in storage and updates 
    the database record.
    """
    return await file_service.complete_upload(db, chat_id, file_id)


@router.get(
    "/chats/{chat_id}/files",
    response_model=list[FileResponse],
    summary="List all files in a chat",
)
async def list_files_endpoint(
    chat_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all files associated with a specific chat."""
    return await file_service.list_files(db, chat_id)


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Delete a file",
)
async def delete_file_endpoint(
    file_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Mark a file for deletion. Asynchronously removes it from storage."""
    arq_pool = request.app.state.arq_pool
    await file_service.delete_file(db, arq_pool, file_id)
    return {"status": "accepted"}
