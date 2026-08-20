from typing import Protocol
from dataclasses import dataclass


@dataclass
class SpeakerSegment:
    """A segment of audio attributed to a specific speaker."""
    speaker: str       # e.g., "speaker_1", "speaker_2"
    start: float       # global seconds
    end: float         # global seconds


class DiarizationProvider(Protocol):
    """Interface for Speaker Diarization providers."""
    
    async def diarize(self, audio_path: str) -> list[SpeakerSegment]:
        """
        Process an audio file and return speaker segments.
        Timestamps are relative to the beginning of the provided audio file.
        """
        ...
