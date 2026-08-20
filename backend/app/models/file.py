"""File model — represents an uploaded media object in storage."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin
from app.models.enums import MediaType, UploadStatus


class File(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A media file uploaded to object storage (MinIO / R2).

    The file record is created when a presigned URL is requested
    (status=pending) and transitions to uploaded when the browser
    confirms the upload completed.
    """

    __tablename__ = "files"

    # ── Parent ───────────────────────────────────────────────────
    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── File metadata ────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    media_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # ── Storage location ─────────────────────────────────────────
    storage_key: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    # ── Lifecycle ────────────────────────────────────────────────
    upload_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UploadStatus.PENDING.value,
        server_default=UploadStatus.PENDING.value,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # ── Relationships ────────────────────────────────────────────
    chat: Mapped["Chat"] = relationship(back_populates="files")  # noqa: F821
    meetings: Mapped[list["Meeting"]] = relationship(  # noqa: F821
        back_populates="file",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<File id={self.id} filename={self.filename!r} "
            f"media_type={self.media_type} status={self.upload_status}>"
        )
