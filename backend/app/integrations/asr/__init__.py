from app.config import get_settings
from app.integrations.asr.base import ASRProvider, ASRSegment
from app.integrations.asr.groq_whisper import GroqWhisperProvider
from app.integrations.asr.local_whisper import FasterWhisperProvider

_asr_provider_instance: ASRProvider | None = None

def get_asr_provider() -> ASRProvider:
    """Factory to get the configured ASR provider."""
    global _asr_provider_instance
    if _asr_provider_instance is not None:
        return _asr_provider_instance
        
    settings = get_settings()
    
    if settings.asr_provider == "groq":
        _asr_provider_instance = GroqWhisperProvider()
    elif settings.asr_provider == "local":
        _asr_provider_instance = FasterWhisperProvider()
    else:
        raise ValueError(f"Unsupported ASR provider: {settings.asr_provider}")
        
    return _asr_provider_instance
