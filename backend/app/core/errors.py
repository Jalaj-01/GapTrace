"""Centralized backend error handling and custom domain exceptions."""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.logging import get_logger

logger = get_logger("app.errors")


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details or {}


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            details=details,
        )


class InvalidFileTypeError(AppException):
    """Unsupported or invalid file extension / MIME type."""

    def __init__(self, message: str = "Invalid file type. Only PDF documents are supported.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            code="INVALID_FILE_TYPE",
            details=details,
        )


class FileTooLargeError(AppException):
    """Payload exceeds maximum allowed file size."""

    def __init__(self, message: str = "Uploaded file size exceeds maximum allowed limit.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413),
            code="FILE_TOO_LARGE",
            details=details,
        )


class CorruptedPDFError(AppException):
    """PDF file cannot be parsed or is corrupted."""

    def __init__(self, message: str = "The uploaded PDF file is corrupted or unreadable.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            code="CORRUPTED_PDF",
            details=details,
        )


class DuplicatePaperError(AppException):
    """Paper with identical hash or content already ingested."""

    def __init__(self, message: str = "A paper with identical content has already been uploaded.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            code="DUPLICATE_PAPER",
            details=details,
        )


class DatabaseConnectionError(AppException):
    """Database connectivity failure."""

    def __init__(self, message: str = "Database connection unavailable", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="DATABASE_UNAVAILABLE",
            details=details,
        )


class LLMProviderError(AppException):
    """LLM provider failure or misconfiguration."""

    def __init__(self, message: str = "LLM provider operation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="LLM_PROVIDER_ERROR",
            details=details,
        )


class NLPProcessingError(AppException):
    """NLP pipeline or model failure."""

    def __init__(self, message: str = "NLP pipeline error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="NLP_PROCESSING_ERROR",
            details=details,
        )


def register_error_handlers(app: FastAPI) -> None:
    """Registers centralized exception handlers to the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.error(
            f"AppException: {exc.code} - {exc.message} [Path: {request.url.path}]",
            extra={"details": exc.details, "path": str(request.url)},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        logger.warning(f"HTTPException: {exc.status_code} - {exc.detail} [Path: {request.url.path}]")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": str(exc.detail),
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                    "path": request.url.path,
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred. Please consult backend logs.",
                    "path": request.url.path,
                },
            },
        )
