from typing import Optional
from app.config import get_settings
from app.integrations.diarization.base import DiarizationProvider

def get_diarization_provider() -> Optional[DiarizationProvider]:
    """
    Factory to get the configured Diarization provider.
    Returns None if diarization is disabled.
    """
    settings = get_settings()
    
    if not settings.diarization_enabled:
        return None
        
    # We will implement providers here later.
    raise NotImplementedError("Diarization providers are not yet implemented")
