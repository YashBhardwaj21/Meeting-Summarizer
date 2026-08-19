"""FastAPI middleware and exception handlers."""

import logging
import uuid
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorResponse, ErrorDetail
from app.utils.exceptions import AppException

logger = logging.getLogger(__name__)


def setup_middleware(app: FastAPI) -> None:
    """Register all middleware and exception handlers."""

    @app.middleware("http")
    async def request_id_and_logging_middleware(request: Request, call_next):
        """Injects a request ID and logs the request duration."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()
        
        try:
            response = await call_next(request)
        except Exception as exc:
            # We catch unhandled exceptions here to log them with request_id, 
            # then re-raise for the exception handlers below.
            logger.error(
                f"Unhandled exception processing request {request_id}", 
                exc_info=exc
            )
            raise
            
        process_time = time.perf_counter() - start_time
        
        # Log successful/handled requests
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"completed with status {response.status_code} in {process_time:.4f}s"
        )
        
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """Transforms known AppException into standardized JSONError response."""
        request_id = getattr(request.state, "request_id", None)
        
        error_detail = ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            request_id=request_id
        )
        
        if exc.status_code >= 500:
            logger.error(f"AppException {exc.error_code}: {exc.message} (Request ID: {request_id})")
        else:
            logger.warning(f"AppException {exc.error_code}: {exc.message} (Request ID: {request_id})")
            
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(error=error_detail).model_dump(exclude_none=True)
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catches all unhandled exceptions and prevents stack traces from leaking."""
        request_id = getattr(request.state, "request_id", None)
        
        logger.error(f"Global exception (Request ID: {request_id})", exc_info=exc)
        
        error_detail = ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            request_id=request_id
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error=error_detail).model_dump(exclude_none=True)
        )
