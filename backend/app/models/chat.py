"""Chat model — the top-level workspace entity."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin
from app.models.enums import ChatStatus


class Chat(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """A chat workspace that owns files, meetings, and messages.

    The chat_id (random UUID) is the access boundary — there is no
    user/auth layer.  All child resources are scoped to a single chat.
    """

    __tablename__ = "chats"

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ChatStatus.ACTIVE.value,
        server_default=ChatStatus.ACTIVE.value,
        index=True,
    )

    # ── Relationships ────────────────────────────────────────────
    files: Mapped[list["File"]] = relationship(  # noqa: F821
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    meetings: Mapped[list["Meeting"]] = relationship(  # noqa: F821
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Chat id={self.id} title={self.title!r} status={self.status}>"
