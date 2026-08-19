"""File Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MediaType, UploadStatus


class PresignRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    content_type: str = Field(..., min_length=1, max_length=100)
    size_bytes: int = Field(..., gt=0)


class PresignResponse(BaseModel):
    file_id: uuid.UUID
    upload_url: str
    expires_in: int


class FileResponse(BaseModel):
    id: uuid.UUID
    filename: str
    media_type: MediaType
    mime_type: str
    size_bytes: int
    upload_status: UploadStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
