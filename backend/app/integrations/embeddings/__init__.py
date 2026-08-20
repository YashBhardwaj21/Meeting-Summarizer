from typing import Optional
from app.config import get_settings
from app.integrations.embeddings.base import EmbeddingProvider
from app.integrations.embeddings.openai_embeddings import OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    """Factory to get the configured Embedding provider."""
    settings = get_settings()
    
    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()
    else:
        raise ValueError(f"Unsupported Embedding provider: {settings.embedding_provider}")
