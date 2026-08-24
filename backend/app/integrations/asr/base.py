from typing import Protocol
from dataclasses import dataclass


@dataclass
class ASRSegment:
    """A segment of transcribed text with relative timestamps."""
    start: float      # chunk-local seconds
    end: float        # chunk-local seconds
    text: str
    words: list[dict] | None = None
    # NO speaker field. Whisper does not do diarization.


class ASRProvider(Protocol):
    """Interface for Automatic Speech Recognition providers."""
    
    async def transcribe(self, audio_path: str) -> list[ASRSegment]:
        """
        Transcribe an audio file and return text segments.
        Timestamps in ASRSegments are relative to the beginning of the provided audio file.
        """
        ...
