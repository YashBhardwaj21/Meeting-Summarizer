import uuid
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_chunk import TranscriptChunk
from app.models.meeting import Meeting
from app.models.enums import MeetingStatus
from app.utils.exceptions import NotFoundError, PermanentProcessingError
from app.integrations.embeddings import get_embedding_provider
from app.integrations.llm.ollama_llm import OllamaGemmaProvider

class RAGService:
    """Service to handle RAG (Retrieval-Augmented Generation) queries against meetings."""
    
    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.llm_provider = OllamaGemmaProvider()
        
    async def ask_question(self, db: AsyncSession, chat_id: uuid.UUID, question: str, limit: int = 10) -> str:
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
            .order_by(TranscriptChunk.embedding.cosine_distance(question_embedding))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            return "No transcript context available to answer your question. Is the meeting finished processing?"
            
        # 3. Construct the prompt
        context_parts = []
        for chunk in chunks:
            # Optionally include timestamps if available, e.g., [MM:SS]
            # Since we just have chunk text, we provide it directly.
            start_min = int(chunk.start_time // 60)
            start_sec = int(chunk.start_time % 60)
            context_parts.append(f"[{start_min:02d}:{start_sec:02d}] {chunk.text}")
            
        context_block = "\n\n".join(context_parts)
        
        system_prompt = (
            "You are a helpful assistant answering questions based on meeting transcripts. "
            "Use the provided context to answer the user's question accurately. "
            "If the answer is not in the context, say you don't know based on the provided transcripts. "
            "Include timestamp references like [MM:SS] when quoting or referring to specific points."
        )
        
        user_prompt = (
            f"Context from meetings:\n"
            f"---\n"
            f"{context_block}\n"
            f"---\n\n"
            f"Question: {question}"
        )
        
        # 4. Generate the answer
        try:
            answer = await self.llm_provider.generate_response(system_prompt, user_prompt)
            return answer
        except Exception as e:
            raise PermanentProcessingError(f"Failed to generate answer: {e}")
            
rag_service = RAGService()
