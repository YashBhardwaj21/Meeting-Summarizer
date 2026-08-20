"""Meeting model — represents a processed media file with extracted intelligence."""

from __future__ import annotations

import uuid
from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin
from app.models.enums import MeetingStatus


class Meeting(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A meeting created from an uploaded audio/video file.

    This represents the "processed" entity that will eventually hold
    transcripts, decisions, action items, etc.
    """

    __tablename__ = "meetings"

    # ── Parents ──────────────────────────────────────────────────
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Meeting details ──────────────────────────────────────────
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MeetingStatus.PENDING.value,
        server_default=MeetingStatus.PENDING.value,
        index=True,
    )
    duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    
    # Optional metadata extracted during processing (e.g. video resolution)
    media_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────
    chat: Mapped["Chat"] = relationship(back_populates="meetings")  # noqa: F821
    file: Mapped["File"] = relationship(back_populates="meetings")  # noqa: F821
    jobs: Mapped[list["ProcessingJob"]] = relationship(  # noqa: F821
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # Transcript segments and chunks
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chunks: Mapped[list["TranscriptChunk"]] = relationship(
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} status={self.status}>"
