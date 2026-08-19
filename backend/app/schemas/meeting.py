"""Meeting Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MeetingStatus


class MeetingCreateRequest(BaseModel):
    file_id: uuid.UUID


class MeetingResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    file_id: uuid.UUID
    title: str | None
    status: MeetingStatus
    duration_seconds: float | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
