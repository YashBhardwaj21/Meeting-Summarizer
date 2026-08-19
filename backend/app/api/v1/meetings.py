"""Meeting API routes."""

import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services import meeting_service

router = APIRouter(tags=["meetings"])


@router.post(
    "/chats/{chat_id}/meetings",
    status_code=status.HTTP_201_CREATED,
    summary="Create a meeting and start processing",
)
async def create_meeting_endpoint(
    chat_id: uuid.UUID,
    payload: MeetingCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a meeting from an uploaded file and enqueues a background processing job.
    Returns both the meeting details and the job tracking ID.
    """
    arq_pool = request.app.state.arq_pool
    
    meeting, job = await meeting_service.create_meeting(
        db=db,
        arq_pool=arq_pool,
        chat_id=chat_id,
        file_id=payload.file_id,
    )
    
    return {
        "meeting": MeetingResponse.model_validate(meeting).model_dump(mode="json"),
        "job_id": job.id,
        "job_status": job.status,
    }


@router.get(
    "/meetings/{meeting_id}",
    response_model=MeetingResponse,
    summary="Get meeting details",
)
async def get_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve details and processing status of a meeting."""
    return await meeting_service.get_meeting(db, meeting_id)
