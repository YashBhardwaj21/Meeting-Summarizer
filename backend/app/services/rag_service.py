import uuid
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_chunk import TranscriptChunk
from app.models.transcript import TranscriptSegment
from app.models.meeting import Meeting
from app.models.enums import MeetingStatus
from app.utils.exceptions import NotFoundError, PermanentProcessingError
from app.integrations.embeddings import get_embedding_provider
from app.integrations.llm.ollama_gemma import OllamaGemmaProvider

class RAGService:
    """Service to handle RAG (Retrieval-Augmented Generation) queries against meetings."""
    
    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.llm_provider = OllamaGemmaProvider()
        
    async def ask_question(self, db: AsyncSession, chat_id: uuid.UUID, question: str, limit: int = 10) -> tuple[str, list[dict[str, Any]]]:
        """
        Ask a question over the transcript chunks of a chat workspace.
        """
        # 1. Embed the user question
        try:
            embeddings = await self.embedding_provider.embed_batch([question])
            question_embedding = embeddings[0]
        except Exception as e:
            raise PermanentProcessingError(f"Failed to embed question: {e}")
            
        # 2. Retrieve top chunks using pgvector (L2 distance or cosine similarity)
        # pgvector uses `<->` for L2 distance, `<#>` for negative inner product, `<=>` for cosine distance
        # We will use cosine distance `<=>`
        stmt = (
            select(TranscriptChunk)
            .where(TranscriptChunk.chat_id == chat_id)
            .where(TranscriptChunk.embedding.is_not(None))
            .order_by(TranscriptChunk.embedding.cosine_distance(question_embedding))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            return "No transcript context available to answer your question. Is the meeting finished processing?", []
            
        # 3. Construct the prompt
        context_parts = []
        for chunk in chunks:
            # Look up speaker from the database
            speaker = None
            if chunk.segment_ids:
                seg_stmt = select(TranscriptSegment.speaker).where(TranscriptSegment.id == chunk.segment_ids[0])
                seg_res = await db.execute(seg_stmt)
                speaker = seg_res.scalar_one_or_none()
            
            speaker_label = speaker or "Unknown"
            
            # Format time as MM:SS
            start_min = int(chunk.start_time // 60)
            start_sec = int(chunk.start_time % 60)
            end_min = int(chunk.end_time // 60)
            end_sec = int(chunk.end_time % 60)
            
            time_block = f"{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}"
            
            context_parts.append(f"[{time_block} | {speaker_label}]\n{chunk.text}")
            
        context_block = "\n\n".join(context_parts)
        
        system_prompt = (
            "You answer questions only from the supplied meeting transcript context. "
            "If the context does not contain the answer, say you do not know. "
            "Do not invent facts."
        )
        
        user_prompt = (
            f"CONTEXT:\n"
            f"{context_block}\n\n"
            f"USER: {question}"
        )
        
        # 4. Generate the answer
        try:
            answer = await self.llm_provider.generate_response(system_prompt, user_prompt)
            
            # Format sources
            sources = []
            for chunk in chunks:
                speaker = None
                if chunk.segment_ids:
                    seg_stmt = select(TranscriptSegment.speaker).where(TranscriptSegment.id == chunk.segment_ids[0])
                    seg_res = await db.execute(seg_stmt)
                    speaker = seg_res.scalar_one_or_none()
                    
                sources.append({
                    "meeting_id": str(chunk.meeting_id),
                    "chunk_id": str(chunk.id),
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "speaker": speaker,
                    "text": chunk.text
                })
                
            return answer, sources
        except Exception as e:
            raise PermanentProcessingError(f"Failed to generate answer: {e}")
            
rag_service = RAGService()
