import logging
from app.config import get_settings
from app.exceptions import PermanentProcessingError, RetryableProcessingError
from app.integrations.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI implementation for text embeddings."""
    
    def __init__(self):
        import openai
        
        settings = get_settings()
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment")
            
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            max_retries=settings.embedding_max_retries,
            timeout=settings.embedding_timeout_seconds
        )
        self._model = settings.embedding_model
        self._dimensions = settings.embedding_dimensions
        self._max_input_tokens = settings.embedding_max_input_tokens
        
    @property
    def dimensions(self) -> int:
        return self._dimensions
        
    @property
    def model_name(self) -> str:
        return self._model
        
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import openai
        
        if not texts:
            return []
            
        try:
            response = await self.client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions if "text-embedding-3" in self._model else None
            )
            
            # The API might return them out of order if we aren't careful, 
            # though it usually returns them in the same order. Sort by index just in case.
            sorted_data = sorted(response.data, key=lambda x: x.index)
            embeddings = [item.embedding for item in sorted_data]
            
            # Dimension validation
            for i, vec in enumerate(embeddings):
                if len(vec) != self._dimensions:
                    raise PermanentProcessingError(
                        f"Embedding dimension mismatch: expected {self._dimensions}, got {len(vec)}",
                        error_code="EMBEDDING_DIMENSION_MISMATCH"
                    )
                    
            return embeddings
            
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            raise RetryableProcessingError(f"Embedding rate limit: {e}", error_code="EMBEDDING_RATE_LIMIT") from e
            
        except (openai.APITimeoutError, openai.APIConnectionError) as e:
            logger.warning(f"OpenAI network error: {e}")
            raise RetryableProcessingError(f"Embedding timeout/connection error: {e}", error_code="EMBEDDING_TIMEOUT") from e
            
        except openai.APIStatusError as e:
            if e.status_code >= 500:
                logger.warning(f"OpenAI server error {e.status_code}: {e}")
                raise RetryableProcessingError(f"Embedding provider error: {e}", error_code="EMBEDDING_PROVIDER_ERROR") from e
            else:
                logger.error(f"OpenAI unexpected status {e.status_code}: {e}")
                # E.g., 400 Bad Request if text is too long, though we should enforce that client-side
                raise PermanentProcessingError(f"Embedding unexpected error: {e}", error_code="EMBEDDING_PROVIDER_ERROR") from e
                
        except Exception as e:
            logger.exception("Unexpected error during OpenAI embedding")
            if isinstance(e, PermanentProcessingError):
                raise
            raise RetryableProcessingError(f"Unexpected embedding error: {e}", error_code="EMBEDDING_PROVIDER_ERROR") from e
