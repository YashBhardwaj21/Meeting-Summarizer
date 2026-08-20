"""Transcript chunk models for semantic retrieval and vector embeddings."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TranscriptChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A chunk of transcription prepared for vector search.
    
    Contains semantic text boundaries, optionally an embedding vector,
    and references back to the original segments (provenance).
    """

    __tablename__ = "transcript_chunks"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chat_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Optional because it's populated in a later stage than chunking
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    
    # Provenance metadata - list of source TranscriptSegment IDs (not relational FK)
    segment_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("meeting_id", "sequence"),
        CheckConstraint("start_time >= 0", name="chk_chunk_start_positive"),
        CheckConstraint("end_time > start_time", name="chk_chunk_end_after_start"),
    )
