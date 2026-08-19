"""Chat Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ChatStatus


class ChatCreate(BaseModel):
    title: str | None = None


class ChatResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    status: ChatStatus
    created_at: datetime
    
    # Aggregated fields (default to 0 if not joined)
    file_count: int = 0
    meeting_count: int = 0

    model_config = ConfigDict(from_attributes=True)
