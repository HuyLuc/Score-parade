"""
Custom exceptions for the application
"""
from typing import Any, Optional
from fastapi import status


class CustomException(Exception):
    """Base exception class for all custom exceptions"""
    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_ERROR"
    ):
        self.detail = detail
        self.status_code = status_code
        self.code = code
        super().__init__(detail)


class ValidationException(CustomException):
    """Raised when validation fails"""
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR"
        )
        self.field = field


class NotFoundException(CustomException):
    """Raised when a resource is not found"""
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            detail=f"{resource} with id {identifier} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND"
        )


class AuthenticationException(CustomException):
    """Raised when authentication fails"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="AUTHENTICATION_ERROR"
        )


class AuthorizationException(CustomException):
    """Raised when user lacks permissions"""
    def __init__(self, detail: str = "You don't have permission to access this resource"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            code="AUTHORIZATION_ERROR"
        )


class DatabaseException(CustomException):
    """Raised when database operations fail"""
    def __init__(self, detail: str):
        super().__init__(
            detail=f"Database error: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR"
        )


class CameraException(CustomException):
    """Raised when camera operations fail"""
    def __init__(self, detail: str, camera_id: Optional[int] = None):
        message = f"Camera {camera_id}: {detail}" if camera_id else detail
        super().__init__(
            detail=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="CAMERA_ERROR"
        )


class AIException(CustomException):
    """Raised when AI processing fails"""
    def __init__(self, detail: str):
        super().__init__(
            detail=f"AI processing error: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="AI_ERROR"
        )
