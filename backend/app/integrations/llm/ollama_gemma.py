import httpx
import logging
from typing import AsyncGenerator

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError

logger = logging.getLogger(__name__)

class OllamaGemmaProvider:
    """Local LLM integration using Ollama and Gemma 3."""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.ollama_base_url.rstrip("/")
        self._model = "gemma3:4b"
        self._timeout = 120.0
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout
        )
        
    @property
    def model_name(self) -> str:
        return self._model
        
    async def generate_response(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a single response (non-streaming) using the chat API."""
        try:
            response = await self.client.post(
                "/api/chat",
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error {response.status_code}: {response.text}")
                raise RetryableProcessingError(f"Ollama server error {response.status_code}", error_code="LLM_PROVIDER_ERROR")

            data = response.json()
            return data.get("message", {}).get("content", "")
            
        except httpx.ConnectError as e:
            logger.warning(f"Ollama connection error: {e}")
            raise RetryableProcessingError(f"Ollama connection error: {e}", error_code="LLM_TIMEOUT") from e
        except Exception as e:
            logger.exception("Unexpected error during Ollama generation")
            raise RetryableProcessingError(f"Unexpected LLM error: {e}", error_code="LLM_PROVIDER_ERROR") from e
            
    async def close(self):
        await self.client.aclose()
