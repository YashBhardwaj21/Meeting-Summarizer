"""Pydantic schemas for transcripts."""

import uuid

from pydantic import BaseModel


class TranscriptSegmentResponse(BaseModel):
    """API response model for a single transcript segment."""

    id: uuid.UUID
    speaker: str | None
    start_time: float
    end_time: float
    text: str


class TranscriptResponse(BaseModel):
    """API response model for a paginated meeting transcript."""

    meeting_id: uuid.UUID
    total_segments: int
    segments: list[TranscriptSegmentResponse]
