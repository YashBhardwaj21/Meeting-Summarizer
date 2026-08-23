from typing import Optional
from app.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.nomic_embeddings import NomicEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Factory to get the configured Embedding provider."""
    settings = get_settings()
    
    if settings.embedding_provider == "nomic":
        return NomicEmbeddingProvider()
    else:
        raise ValueError(f"Unsupported Embedding provider: {settings.embedding_provider}")
