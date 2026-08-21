import httpx
import logging
from typing import Any
from pydantic import BaseModel

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError
from app.integrations.asr.base import ASRProvider, ASRSegment

logger = logging.getLogger(__name__)


class GroqWhisperProvider(ASRProvider):
    """
    Groq Whisper Large v3 Turbo integration for ASR.
    Uses httpx for async API requests to avoid the sync groq library blocking the event loop,
    or we can use the async Groq client if installed.
    Since we installed `groq`, we will use `groq.AsyncGroq`.
    """

    def __init__(self):
        # Import here to avoid issues if not installed
        import groq
        
        settings = get_settings()
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY must be set in environment")
            
        self.client = groq.AsyncGroq(
            api_key=settings.groq_api_key,
            max_retries=settings.asr_max_retries,
            timeout=settings.asr_timeout_seconds
        )
        self.model = settings.asr_model

    async def transcribe(self, audio_path: str) -> list[ASRSegment]:
        import groq
        
        try:
            with open(audio_path, "rb") as file:
                transcription = await self.client.audio.transcriptions.create(
                    file=(audio_path, file.read()),
                    model=self.model,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    temperature=0.0
                )
                
            segments = []
            
            # The verbose_json response returns a dict-like object (or BaseModel in newer SDKs)
            # We access the 'segments' property.
            if hasattr(transcription, "segments") and transcription.segments:
                raw_segments = transcription.segments
            elif isinstance(transcription, dict) and "segments" in transcription:
                raw_segments = transcription["segments"]
            else:
                raise PermanentProcessingError("No segments found in Groq response", error_code="ASR_EMPTY_RESULT")
                
            if not raw_segments:
                raise PermanentProcessingError("Empty segments list in Groq response", error_code="ASR_EMPTY_RESULT")
                
            for seg in raw_segments:
                # Handle both dicts and objects
                if isinstance(seg, dict):
                    start = float(seg["start"])
                    end = float(seg["end"])
                    text = str(seg["text"]).strip()
                else:
                    start = float(seg.start)
                    end = float(seg.end)
                    text = str(seg.text).strip()
                    
                if not text:
                    continue
                    
                segments.append(ASRSegment(
                    start=start,
                    end=end,
                    text=text
                ))
                
            return segments

        except groq.RateLimitError as e:
            logger.warning(f"Groq rate limit exceeded: {e}")
            raise RetryableProcessingError(f"ASR rate limit: {e}", error_code="ASR_RATE_LIMIT") from e
            
        except (groq.APITimeoutError, groq.APIConnectionError) as e:
            logger.warning(f"Groq network error: {e}")
            raise RetryableProcessingError(f"ASR timeout/connection error: {e}", error_code="ASR_TIMEOUT") from e
            
        except groq.APIStatusError as e:
            if e.status_code >= 500:
                logger.warning(f"Groq server error {e.status_code}: {e}")
                raise RetryableProcessingError(f"ASR provider error: {e}", error_code="ASR_PROVIDER_ERROR") from e
            elif e.status_code == 413:
                logger.error(f"Groq file too large: {e}")
                raise PermanentProcessingError("Audio file too large for ASR", error_code="ASR_FILE_TOO_LARGE") from e
            elif e.status_code in (400, 415):
                logger.error(f"Groq bad request / unsupported media: {e}")
                raise PermanentProcessingError("Invalid audio format for ASR", error_code="ASR_UNSUPPORTED_FORMAT") from e
            else:
                logger.error(f"Groq unexpected status {e.status_code}: {e}")
                raise PermanentProcessingError(f"ASR unexpected error: {e}", error_code="ASR_PROVIDER_ERROR") from e
                
        except Exception as e:
            logger.exception("Unexpected error during Groq transcription")
            if isinstance(e, PermanentProcessingError):
                raise
            raise RetryableProcessingError(f"Unexpected ASR error: {e}", error_code="ASR_PROVIDER_ERROR") from e
