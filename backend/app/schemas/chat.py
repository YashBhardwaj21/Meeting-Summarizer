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


class ChatSource(BaseModel):
    meeting_id: uuid.UUID
    chunk_id: uuid.UUID
    start_time: float
    end_time: float
    speaker: str | None = None
    text: str


from pydantic import BaseModel, ConfigDict, Field

class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    chat_id: uuid.UUID
    role: str
    message_type: str = "text"
    content: str | None = None
    meeting_id: uuid.UUID | None = None
    metadata_: dict | None = Field(default=None, serialization_alias="metadata")
    created_at: datetime
    sources: list[ChatSource] | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AskQuestionRequest(BaseModel):
    question: str
    limit: int = 10


class AskQuestionResponse(BaseModel):
    message: ChatMessageResponse
    sources: list[ChatSource] | None = None
