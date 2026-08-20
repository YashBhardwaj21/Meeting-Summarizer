"""Shared exception classes for the application."""

class AppError(Exception):
    """Base exception for application errors."""
    pass


class StorageError(AppError):
    """Raised when there are issues communicating with object storage."""
    pass


class ProcessingError(AppError):
    """Base class for meeting processing pipeline errors."""
    
    def __init__(self, message: str, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class RetryableProcessingError(ProcessingError):
    """An error that should trigger a retry (e.g. rate limits, network timeouts)."""
    pass


class PermanentProcessingError(ProcessingError):
    """An error that is fatal and should fail the job (e.g. bad format, auth failed)."""
    pass
