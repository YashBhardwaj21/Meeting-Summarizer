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
