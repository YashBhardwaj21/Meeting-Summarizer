from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.models.transcript import TranscriptSegment
from app.models.transcript_chunk import TranscriptChunk
from app.services.transcription_service import CanonicalSegment


async def replace_meeting_transcript(
    db: AsyncSession, 
    meeting_id: UUID, 
    segments: list[CanonicalSegment]
) -> list[TranscriptSegment]:
    """
    Atomic replacement of all transcript segments for a meeting.
    Deletes any existing segments first to ensure idempotent retries.
    """
    # 1. Delete all existing segments for this meeting_id
    await db.execute(
        delete(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
    )
    
    # 2. Insert canonical segments with sequential numbering
    db_segments = []
    for idx, seg in enumerate(segments):
        db_seg = TranscriptSegment(
            meeting_id=meeting_id,
            sequence=idx,
            speaker=seg.speaker,
            start_time=seg.start_time,
            end_time=seg.end_time,
            text=seg.text
        )
        db_segments.append(db_seg)
        db.add(db_seg)
        
    # 3. Commit
    await db.commit()
    
    return db_segments


async def replace_meeting_chunks(
    db: AsyncSession, 
    meeting_id: UUID, 
    chat_id: UUID, 
    chunks: list,  # list of ChunkData (from chunking_service)
    embeddings: list[list[float]],
    model_name: str,
    dimensions: int
) -> list[TranscriptChunk]:
    """
    Atomic replacement of all semantic chunks and embeddings for a meeting.
    Deletes any existing chunks first to ensure idempotent retries.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("Number of chunks and embeddings must match")
        
    # 1. Delete all existing chunks for this meeting_id
    await db.execute(
        delete(TranscriptChunk).where(TranscriptChunk.meeting_id == meeting_id)
    )
    
    # 2. Insert new chunks with embeddings
    db_chunks = []
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        db_chunk = TranscriptChunk(
            meeting_id=meeting_id,
            chat_id=chat_id,
            sequence=idx,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            text=chunk.text,
            embedding=embedding,
            segment_ids=chunk.segment_ids,
            token_count=chunk.token_count,
            embedding_model=model_name,
            embedding_dimensions=dimensions
        )
        db_chunks.append(db_chunk)
        db.add(db_chunk)
        
    # 3. Commit
    await db.commit()
    
    return db_chunks


async def get_transcript(
    db: AsyncSession, 
    meeting_id: UUID, 
    offset: int = 0, 
    limit: int = 50
) -> tuple[list[TranscriptSegment], int]:
    """
    Get paginated segments ordered by sequence, and the total count.
    """
    # Get total count
    count_stmt = select(func.count()).select_from(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
    total_result = await db.execute(count_stmt)
    total_segments = total_result.scalar_one_or_none() or 0
    
    if total_segments == 0:
        return [], 0
        
    # Get paginated segments
    stmt = (
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.sequence)
        .offset(offset)
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    segments = list(result.scalars().all())
    
    return segments, total_segments


async def search_chunks(
    db: AsyncSession, 
    meeting_id: UUID, 
    query_embedding: list[float], 
    limit: int = 8
) -> list[TranscriptChunk]:
    """
    Search chunks in a specific meeting using pgvector cosine similarity.
    """
    # The `<=>` operator in pgvector does cosine distance
    stmt = (
        select(TranscriptChunk)
        .where(TranscriptChunk.meeting_id == meeting_id)
        .order_by(TranscriptChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())
