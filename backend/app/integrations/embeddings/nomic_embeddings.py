import httpx
import logging
from typing import List

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError
from app.integrations.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class NomicEmbeddingProvider(EmbeddingProvider):
    """Local embedding integration using Ollama and Nomic."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self._model = settings.embedding_model or "nomic-embed-text"
        self._dimensions = settings.embedding_dimensions or 768
        self._timeout = settings.embedding_timeout_seconds or 60
        self._max_retries = settings.embedding_max_retries or 3
        
        # AsyncClient for HTTP calls
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout
        )
        
    @property
    def dimensions(self) -> int:
        return self._dimensions
        
    @property
    def model_name(self) -> str:
        return self._model
        
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
            
        try:
            # The newer Ollama API /api/embed accepts batched inputs
            response = await self.client.post(
                "/api/embed",
                json={
                    "model": self._model,
                    "input": texts,
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error {response.status_code}: {response.text}")
                if response.status_code >= 500:
                    raise RetryableProcessingError(f"Ollama server error {response.status_code}", error_code="EMBEDDING_PROVIDER_ERROR")
                elif response.status_code == 404:
                    raise PermanentProcessingError(f"Model '{self._model}' not found in Ollama. Run 'ollama pull {self._model}'", error_code="EMBEDDING_MODEL_NOT_FOUND")
                else:
                    raise PermanentProcessingError(f"Ollama embedding unexpected error {response.status_code}", error_code="EMBEDDING_PROVIDER_ERROR")

            data = response.json()
            embeddings = data.get("embeddings", [])
            
            if not embeddings or len(embeddings) != len(texts):
                raise PermanentProcessingError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}",
                    error_code="EMBEDDING_PROVIDER_ERROR"
                )
            
            # Dimension validation
            for i, vec in enumerate(embeddings):
                if len(vec) != self._dimensions:
                    raise PermanentProcessingError(
                        f"Embedding dimension mismatch: expected {self._dimensions}, got {len(vec)}",
                        error_code="EMBEDDING_DIMENSION_MISMATCH"
                    )
                    
            return embeddings
            
        except httpx.ConnectError as e:
            logger.warning(f"Ollama connection error: {e}")
            raise RetryableProcessingError(f"Ollama connection error: {e}", error_code="EMBEDDING_TIMEOUT") from e
        except httpx.TimeoutException as e:
            logger.warning(f"Ollama timeout error: {e}")
            raise RetryableProcessingError(f"Ollama timeout error: {e}", error_code="EMBEDDING_TIMEOUT") from e
        except Exception as e:
            logger.exception("Unexpected error during Ollama embedding")
            if isinstance(e, PermanentProcessingError) or isinstance(e, RetryableProcessingError):
                raise
            raise RetryableProcessingError(f"Unexpected embedding error: {e}", error_code="EMBEDDING_PROVIDER_ERROR") from e

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()
