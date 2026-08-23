import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pyannote.audio import Pipeline

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError
from app.integrations.diarization.base import DiarizationProvider, SpeakerSegment

logger = logging.getLogger(__name__)

# Executor for CPU-bound diarization
_executor = ThreadPoolExecutor(max_workers=1)

class PyannoteDiarizationProvider(DiarizationProvider):
    """
    Local Diarization integration using pyannote/speaker-diarization-community-1.
    """
    
    def __init__(self):
        settings = get_settings()
        
        if not settings.hf_token:
            logger.error("Hugging Face token not provided for pyannote.audio.")
            raise PermanentProcessingError("Hugging Face token (HF_TOKEN) is required for diarization.", error_code="DIARIZATION_TOKEN_MISSING")
            
        self.model_name = settings.diarization_model or "pyannote/speaker-diarization-community-1"
        
        logger.info(f"Loading Pyannote diarization pipeline '{self.model_name}'")
        
        try:
            self.pipeline = Pipeline.from_pretrained(
                self.model_name,
                use_auth_token=settings.hf_token
            )
            # Pyannote uses `use_auth_token` in 3.1+ pipelines.
            if self.pipeline is None:
                raise RuntimeError(f"Could not load pyannote pipeline {self.model_name}. Please check HF_TOKEN.")
                
            # Optionally move to CUDA if desired, but we default to CPU for offline compatibility
            import torch
            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))
                
            logger.info("Pyannote diarization pipeline loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load pyannote pipeline: {e}")
            raise PermanentProcessingError(f"Failed to load Diarization model: {e}", error_code="DIARIZATION_MODEL_LOAD_FAILED") from e

    def _diarize_sync(self, audio_path: str) -> list[SpeakerSegment]:
        """Synchronous wrapper for pyannote diarization."""
        try:
            logger.info(f"Running pyannote diarization on {audio_path}")
            diarization = self.pipeline(audio_path)
            
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(SpeakerSegment(
                    speaker=speaker,
                    start=float(turn.start),
                    end=float(turn.end)
                ))
                
            return segments
            
        except Exception as e:
            logger.exception("Error during pyannote diarization")
            raise PermanentProcessingError(f"Local Diarization error: {e}", error_code="DIARIZATION_PROVIDER_ERROR") from e

    async def diarize(self, audio_path: str) -> list[SpeakerSegment]:
        """Async wrapper using ThreadPoolExecutor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(_executor, self._diarize_sync, audio_path)
