"""ProcessingJob model — tracks background tasks for processing meetings."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import JobStatus


class ProcessingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A background job for processing an uploaded file into meeting insights.

    Jobs have a status, a specific stage (e.g., 'transcription'),
    and tracking for retries and errors.
    """

    __tablename__ = "processing_jobs"

    # ── Parents ──────────────────────────────────────────────────
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Job tracking ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JobStatus.QUEUED.value,
        server_default=JobStatus.QUEUED.value,
        index=True,
    )
    stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # ── Retries & Errors ─────────────────────────────────────────
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )
    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    processing_metrics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ── Timestamps ───────────────────────────────────────────────
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────
    file: Mapped["File"] = relationship()  # noqa: F821
    meeting: Mapped["Meeting"] = relationship(back_populates="jobs")  # noqa: F821

    def __repr__(self) -> str:
        return (
            f"<ProcessingJob id={self.id} status={self.status} "
            f"stage={self.stage} attempts={self.attempt_count}>"
        )
