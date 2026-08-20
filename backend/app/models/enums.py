"""Database enum types mapped to PostgreSQL enums."""

import enum


class ChatStatus(str, enum.Enum):
    """Lifecycle status of a chat workspace."""

    ACTIVE = "active"
    DELETING = "deleting"
    DELETED = "deleted"


class MediaType(str, enum.Enum):
    """Whether the uploaded file is audio or video."""

    AUDIO = "audio"
    VIDEO = "video"


class UploadStatus(str, enum.Enum):
    """Lifecycle status of a file upload."""

    PENDING = "pending"      # Presigned URL issued, upload not yet confirmed
    UPLOADED = "uploaded"    # Upload confirmed, object exists in storage
    FAILED = "failed"        # Upload failed or was abandoned


class MeetingStatus(str, enum.Enum):
    """Processing status of a meeting."""

    PENDING = "pending"        # Meeting created, job not yet picked up
    PROCESSING = "processing"  # Worker is actively processing
    READY = "ready"            # All processing complete, queryable
    FAILED = "failed"          # Processing failed after max retries


class JobStatus(str, enum.Enum):
    """Status of a background processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
