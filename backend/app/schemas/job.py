"""ProcessingJob Pydantic schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus


class JobResponse(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    status: JobStatus
    stage: str | None
    attempt_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
