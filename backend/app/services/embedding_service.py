from app.integrations.embeddings.base import EmbeddingProvider
from app.services.chunking_service import ChunkData
from app.utils.exceptions import PermanentProcessingError

async def embed_chunks(
    chunks: list[ChunkData], 
    provider: EmbeddingProvider, 
    batch_size: int = 32
) -> list[list[float]]:
    """
    Generate embeddings for semantic chunks in batches.
    NEVER call this inside a DB transaction to avoid holding locks during network I/O.
    """
    if not chunks:
        return []
        
    all_embeddings = []
    
    # Process in batches
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk.text for chunk in batch]
        
        embeddings = await provider.embed_batch(texts)
        all_embeddings.extend(embeddings)
        
    if len(all_embeddings) != len(chunks):
        raise PermanentProcessingError(
            f"Expected {len(chunks)} embeddings, got {len(all_embeddings)}",
            error_code="EMBEDDING_COUNT_MISMATCH"
        )
        
    return all_embeddings
