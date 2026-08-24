import logging
import httpx
from typing import List

from app.config import get_settings
from app.utils.exceptions import PermanentProcessingError, RetryableProcessingError
from app.integrations.diarization.base import DiarizationProvider, SpeakerSegment

logger = logging.getLogger(__name__)


class RemoteDiarizationProvider(DiarizationProvider):
    """
    Remote Diarization integration using an external Colab T4 endpoint.
    Sends normalized audio to a remote server for Pyannote Community-1 GPU diarization.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.remote_url = self.settings.diarization_remote_url.rstrip("/")
        self.api_key = self.settings.diarization_api_key
        self.timeout = self.settings.diarization_timeout_seconds
        
        if not self.remote_url:
            raise PermanentProcessingError(
                "DIARIZATION_REMOTE_URL is not set but provider is 'remote'",
                error_code="DIARIZATION_CONFIG_ERROR"
            )

    async def diarize(self, audio_path: str) -> List[SpeakerSegment]:
        """Send audio file to remote endpoint for diarization."""
        logger.info(f"Sending {audio_path} to remote diarization endpoint: {self.remote_url}")
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        try:
            # We open the file in binary mode and pass it via a multipart form
            with open(audio_path, "rb") as f:
                files = {
                    "audio": ("audio.wav", f, "audio/wav")
                }
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.remote_url}/diarize",
                        files=files,
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        error_msg = f"Remote diarization failed with status {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        
                        if response.status_code >= 500:
                            raise RetryableProcessingError(error_msg, error_code="REMOTE_DIARIZATION_ERROR")
                        else:
                            raise PermanentProcessingError(error_msg, error_code="REMOTE_DIARIZATION_ERROR")
                            
                    data = response.json()
                    segments_data = data.get("segments", [])
                    
                    segments = []
                    for item in segments_data:
                        segments.append(
                            SpeakerSegment(
                                speaker=item["speaker"],
                                start=item["start"],
                                end=item["end"]
                            )
                        )
                        
                    logger.info(f"Received {len(segments)} segments from remote diarization")
                    return segments
                    
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to remote diarization endpoint: {e}")
            raise RetryableProcessingError(f"Connection failed: {e}", error_code="REMOTE_DIARIZATION_NETWORK_ERROR") from e
        except httpx.TimeoutException as e:
            logger.error(f"Remote diarization timed out after {self.timeout}s: {e}")
            raise RetryableProcessingError(f"Request timed out: {e}", error_code="REMOTE_DIARIZATION_TIMEOUT") from e
        except Exception as e:
            logger.exception("Unexpected error during remote diarization")
            if isinstance(e, (PermanentProcessingError, RetryableProcessingError)):
                raise
            raise RetryableProcessingError(f"Unexpected error: {e}", error_code="REMOTE_DIARIZATION_UNKNOWN_ERROR") from e
