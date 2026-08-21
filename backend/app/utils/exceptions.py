"""Custom application exceptions."""


class AppException(Exception):
    """Base exception for all application errors."""
    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found (404)."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, "NOT_FOUND", message)


class ConflictError(AppException):
    """Resource state conflict (409)."""
    def __init__(self, message: str = "Resource state conflict"):
        super().__init__(409, "CONFLICT", message)


class ValidationError(AppException):
    """Validation failed (400)."""
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(400, error_code, message)


class StorageError(AppException):
    """Object storage error (500)."""
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(500, "STORAGE_ERROR", message)


class InternalServerError(AppException):
    """Internal server error (500)."""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(500, "INTERNAL_ERROR", message)


class ProcessingError(AppException):
    """Base class for meeting processing pipeline errors."""
    def __init__(self, message: str, error_code: str = "PROCESSING_ERROR"):
        super().__init__(500, error_code, message)


class RetryableProcessingError(ProcessingError):
    """An error that should trigger a retry (e.g. rate limits, network timeouts)."""
    pass


class PermanentProcessingError(ProcessingError):
    """An error that is fatal and should fail the job (e.g. bad format, auth failed)."""
    pass
