from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.meeting import Meeting
from app.services import transcript_service

router = APIRouter()


class TranscriptSegmentResponse(BaseModel):
    id: UUID
    sequence: int
    speaker: Optional[str]
    start_time: float
    end_time: float
    text: str
    
    model_config = ConfigDict(from_attributes=True)


class TranscriptPaginationResponse(BaseModel):
    items: List[TranscriptSegmentResponse]
    total: int
    offset: int
    limit: int


@router.get(
    "/chats/{chat_id}/meetings/{meeting_id}/transcript",
    response_model=TranscriptPaginationResponse,
    description="Get the transcript for a specific meeting."
)
async def get_meeting_transcript(
    chat_id: UUID,
    meeting_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TranscriptPaginationResponse:
    # Verify the meeting exists and belongs to the user via the chat
    # To be perfectly secure, we should verify that `meeting_id` belongs to `chat_id` 
    # and that `chat_id` belongs to `current_user`.
    meeting = await db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.chat_id != chat_id:
        raise HTTPException(status_code=400, detail="Meeting does not belong to this chat")
        
    # Verify chat ownership (we assume user has access if chat is theirs)
    # The models might not be fully loaded, so let's check it.
    chat = await meeting.awaitable_attrs.chat
    if chat.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this meeting")
        
    segments, total = await transcript_service.get_transcript(
        db, meeting_id, offset=offset, limit=limit
    )
    
    return TranscriptPaginationResponse(
        items=[TranscriptSegmentResponse.model_validate(seg) for seg in segments],
        total=total,
        offset=offset,
        limit=limit
    )
