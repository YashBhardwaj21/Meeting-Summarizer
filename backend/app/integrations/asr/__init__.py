from app.config import get_settings
from app.integrations.asr.base import ASRProvider, ASRSegment
from app.integrations.asr.groq_whisper import GroqWhisperProvider
from app.integrations.asr.local_whisper import FasterWhisperProvider

def get_asr_provider() -> ASRProvider:
    """Factory to get the configured ASR provider."""
    settings = get_settings()
    
    if settings.asr_provider == "groq":
        return GroqWhisperProvider()
    elif settings.asr_provider == "local":
        return FasterWhisperProvider()
    else:
        raise ValueError(f"Unsupported ASR provider: {settings.asr_provider}")
