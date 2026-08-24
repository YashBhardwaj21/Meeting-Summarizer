from typing import Optional
from app.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.nomic_embeddings import NomicEmbeddingProvider

_nomic_provider = None

def get_embedding_provider() -> EmbeddingProvider:
    """Factory to get the configured Embedding provider."""
    global _nomic_provider
    settings = get_settings()
    
    if settings.embedding_provider == "nomic":
        if _nomic_provider is None:
            _nomic_provider = NomicEmbeddingProvider()
        return _nomic_provider
    else:
        raise ValueError(f"Unsupported Embedding provider: {settings.embedding_provider}")
