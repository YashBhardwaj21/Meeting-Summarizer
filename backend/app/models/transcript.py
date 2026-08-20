"""Transcript segment models for storing exact text segments."""

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TranscriptSegment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A segment of transcribed audio with start and end times.
    
    Belongs to a specific meeting and has a strict sequence number.
    Speaker is nullable (null means unknown).
    """

    __tablename__ = "transcript_segments"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("meeting_id", "sequence"),
        CheckConstraint("start_time >= 0", name="chk_start_time_positive"),
        CheckConstraint("end_time > start_time", name="chk_end_time_after_start"),
    )
