from typing import Optional
from app.config import get_settings
from app.integrations.diarization.base import DiarizationProvider

_diarization_provider_instance: Optional[DiarizationProvider] = None

def get_diarization_provider() -> Optional[DiarizationProvider]:
    """
    Factory to get the configured Diarization provider.
    Returns None if diarization is disabled.
    """
    global _diarization_provider_instance
    if _diarization_provider_instance is not None:
        return _diarization_provider_instance
        
    settings = get_settings()
    
    if not settings.diarization_enabled:
        return None
        
    if settings.diarization_provider == "remote":
        from app.integrations.diarization.remote import RemoteDiarizationProvider
        _diarization_provider_instance = RemoteDiarizationProvider()
    else:
        from app.integrations.diarization.pyannote_diarization import PyannoteDiarizationProvider
        _diarization_provider_instance = PyannoteDiarizationProvider()
        
    return _diarization_provider_instance
