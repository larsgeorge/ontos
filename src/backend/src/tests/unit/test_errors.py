"""
Unit tests for common error classes

Tests custom error classes including:
- NotFoundError
- ValidationError
- ConflictError
- UnauthorizedError
- ForbiddenError
- InternalServerError
"""
import pytest
from fastapi import status

from src.common.errors import (
    AppError,
    NotFoundError,
    ValidationError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    InternalServerError,
)


class TestErrors:
    """Test suite for error classes"""

    def test_not_found_error_default(self):
        """Test NotFoundError with default message."""
        error = NotFoundError()
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.detail == "Resource not found"

    def test_not_found_error_custom(self):
        """Test NotFoundError with custom message."""
        error = NotFoundError("Custom not found message")
        assert error.status_code == status.HTTP_404_NOT_FOUND
        assert error.detail == "Custom not found message"

    def test_validation_error_default(self):
        """Test ValidationError with default message."""
        error = ValidationError()
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.detail == "Validation error"

    def test_validation_error_custom(self):
        """Test ValidationError with custom message."""
        error = ValidationError("Invalid input format")
        assert error.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert error.detail == "Invalid input format"

    def test_conflict_error_default(self):
        """Test ConflictError with default message."""
        error = ConflictError()
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.detail == "Resource already exists"

    def test_conflict_error_custom(self):
        """Test ConflictError with custom message."""
        error = ConflictError("Duplicate entry detected")
        assert error.status_code == status.HTTP_409_CONFLICT
        assert error.detail == "Duplicate entry detected"

    def test_unauthorized_error_default(self):
        """Test UnauthorizedError with default message."""
        error = UnauthorizedError()
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Unauthorized"

    def test_unauthorized_error_custom(self):
        """Test UnauthorizedError with custom message."""
        error = UnauthorizedError("Invalid credentials")
        assert error.status_code == status.HTTP_401_UNAUTHORIZED
        assert error.detail == "Invalid credentials"

    def test_forbidden_error_default(self):
        """Test ForbiddenError with default message."""
        error = ForbiddenError()
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Forbidden"

    def test_forbidden_error_custom(self):
        """Test ForbiddenError with custom message."""
        error = ForbiddenError("Insufficient permissions")
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert error.detail == "Insufficient permissions"

    def test_internal_server_error_default(self):
        """Test InternalServerError with default message."""
        error = InternalServerError()
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.detail == "Internal server error"

    def test_internal_server_error_custom(self):
        """Test InternalServerError with custom message."""
        error = InternalServerError("Database connection failed")
        assert error.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error.detail == "Database connection failed"

    def test_app_error_base(self):
        """Test AppError base class."""
        error = AppError(status_code=418, detail="I'm a teapot")
        assert error.status_code == 418
        assert error.detail == "I'm a teapot"

    def test_error_inheritance(self):
        """Test that all errors inherit from AppError."""
        assert issubclass(NotFoundError, AppError)
        assert issubclass(ValidationError, AppError)
        assert issubclass(ConflictError, AppError)
        assert issubclass(UnauthorizedError, AppError)
        assert issubclass(ForbiddenError, AppError)
        assert issubclass(InternalServerError, AppError)

    def test_error_raises_correctly(self):
        """Test that errors can be raised and caught."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Test resource not found")
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Test resource not found"

