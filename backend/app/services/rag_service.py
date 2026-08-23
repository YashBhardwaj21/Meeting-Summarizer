import uuid
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_chunk import TranscriptChunk
from app.models.transcript import TranscriptSegment
from app.models.meeting import Meeting
from app.models.enums import MeetingStatus
from app.utils.exceptions import NotFoundError, PermanentProcessingError, RetryableProcessingError
from app.integrations.embeddings import get_embedding_provider
from app.integrations.llm.ollama_gemma import OllamaGemmaProvider

class RAGService:
    """Service to handle RAG (Retrieval-Augmented Generation) queries against meetings."""
    
    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.llm_provider = OllamaGemmaProvider()
        
    async def ask_question(self, db: AsyncSession, chat_id: uuid.UUID, question: str, limit: int = 10, history: list[dict[str, str]] | None = None) -> tuple[str, list[dict[str, Any]]]:
        """
        Ask a question over the transcript chunks of a chat workspace.
        """
        from app.config import get_settings
        settings = get_settings()

        # 1. Embed the retrieval query (follow-up aware)
        if history:
            prev_user_q = ""
            for msg in reversed(history):
                if msg.get("role") == "user":
                    prev_user_q = msg.get("content", "")
                    break
            
            if prev_user_q:
                retrieval_query = f"{prev_user_q} {question}"
            else:
                retrieval_query = question
        else:
            retrieval_query = question

        try:
            embeddings = await self.embedding_provider.embed_batch([retrieval_query])
            question_embedding = embeddings[0]
        except Exception as e:
            raise PermanentProcessingError(f"Failed to embed question: {e}")
            
        # 2. Retrieve top chunks using pgvector (L2 distance or cosine similarity)
        # pgvector uses `<->` for L2 distance, `<#>` for negative inner product, `<=>` for cosine distance
        distance_col = TranscriptChunk.embedding.cosine_distance(question_embedding).label("distance")
        stmt = (
            select(TranscriptChunk, distance_col)
            .where(TranscriptChunk.chat_id == chat_id)
            .where(TranscriptChunk.embedding.is_not(None))
            .order_by(distance_col)
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        rows = result.all()
        
        if not rows:
            return "No transcript context available to answer your question. Is the meeting finished processing?", []
            
        # Check similarity threshold on the best match
        best_distance = rows[0].distance
        best_similarity = 1.0 - best_distance
        
        if best_similarity < settings.rag_similarity_threshold:
            return "I couldn't find enough information in the meeting transcript to answer that.", []
            
        # 3. Construct the prompt and source evidence
        context_parts = []
        sources = []
        
        for row in rows:
            chunk = row.TranscriptChunk
            distance = row.distance
            
            # Fetch ALL segments for this chunk
            segments_data = []
            speakers_set = set()
            
            if chunk.segment_ids:
                seg_stmt = (
                    select(TranscriptSegment)
                    .where(TranscriptSegment.id.in_(chunk.segment_ids))
                    .order_by(TranscriptSegment.start_time)
                )
                seg_res = await db.execute(seg_stmt)
                segments = seg_res.scalars().all()
                
                for seg in segments:
                    spk = seg.speaker or "Unknown"
                    speakers_set.add(spk)
                    segments_data.append({
                        "start_time": seg.start_time,
                        "end_time": seg.end_time,
                        "speaker": spk,
                        "text": seg.text
                    })
            
            speakers_list = list(speakers_set)
            
            # Format time as MM:SS
            start_min = int(chunk.start_time // 60)
            start_sec = int(chunk.start_time % 60)
            end_min = int(chunk.end_time // 60)
            end_sec = int(chunk.end_time % 60)
            time_block = f"{start_min:02d}:{start_sec:02d}-{end_min:02d}:{end_sec:02d}"
            
            speakers_str = ", ".join(speakers_list) if speakers_list else "Unknown"
            
            context_parts.append(f"[{time_block} | {speakers_str}]\n{chunk.text}")
            
            sources.append({
                "meeting_id": str(chunk.meeting_id),
                "chunk_id": str(chunk.id),
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "speaker": speakers_list[0] if speakers_list else None,
                "speakers": speakers_list,
                "segments": segments_data,
                "text": chunk.text
            })
            
        context_block = "\n\n".join(context_parts)
        
        system_prompt = (
            "You are MeetSum, a meeting transcript assistant. Answer using only the supplied transcript evidence. "
            "Rules:\n"
            "- Answer the user's exact question.\n"
            "- Use conversation history to understand follow-up questions.\n"
            "- Do not invent information.\n"
            "- If the evidence is insufficient, say so.\n"
            "- Preserve speaker names when available.\n"
            "- Use timestamps when useful.\n"
            "- Do not claim a person said something unless the evidence identifies that speaker.\n"
            "- Do not mention the retrieval process.\n"
            "- Do not repeat the transcript unnecessarily.\n"
            "- Give a direct answer first, then supporting details if needed."
        )
        
        user_prompt = (
            f"MEETING EVIDENCE:\n"
            f"{context_block}\n\n"
            f"CURRENT QUESTION: {question}"
        )
        
        # 4. Generate the answer
        try:
            answer = await self.llm_provider.generate_response(system_prompt, user_prompt, history=history)
            return answer, sources
        except RetryableProcessingError:
            raise
        except PermanentProcessingError:
            raise
        except Exception as e:
            raise PermanentProcessingError(f"Failed to generate answer: {e}")
            
rag_service = RAGService()
