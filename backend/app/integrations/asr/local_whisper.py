import logging
import asyncio
from typing import Any
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError
from app.integrations.asr.base import ASRProvider, ASRSegment

logger = logging.getLogger(__name__)

# We use a global executor to avoid blocking the asyncio event loop with CPU-bound transcription.
_executor = ThreadPoolExecutor(max_workers=1)

class FasterWhisperProvider(ASRProvider):
    """
    Local Whisper integration using faster-whisper.
    """
    
    def __init__(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError("faster-whisper is not installed. Please install it to use the local ASR provider.")
            
        settings = get_settings()
        
        self.model_size = settings.asr_model or "small"
        self.device = getattr(settings, "whisper_device", "cpu")
        self.compute_type = getattr(settings, "whisper_compute_type", "int8")
        
        logger.info(f"Loading faster-whisper model '{self.model_size}' on {self.device} with compute_type={self.compute_type}")
        
        # Load model immediately upon instantiation
        try:
            import os
            os.makedirs("/app/models", exist_ok=True)
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root="/app/models"
            )
            logger.info("faster-whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            raise PermanentProcessingError(f"Failed to load Whisper model: {e}", error_code="ASR_MODEL_LOAD_FAILED") from e

    def _transcribe_sync(self, audio_path: str) -> list[ASRSegment]:
        """Synchronous wrapper for faster-whisper transcription."""
        try:
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            logger.info(f"Detected language '{info.language}' with probability {info.language_probability}")
            
            asr_segments = []
            for segment in segments:
                text = str(segment.text).strip()
                if not text:
                    continue
                    
                asr_segments.append(ASRSegment(
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text
                ))
                
            return asr_segments
            
        except Exception as e:
            logger.exception("Error during local whisper transcription")
            raise RetryableProcessingError(f"Local ASR error: {e}", error_code="ASR_PROVIDER_ERROR") from e

    async def transcribe(self, audio_path: str) -> list[ASRSegment]:
        """Async wrapper using ThreadPoolExecutor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self._transcribe_sync, audio_path)
