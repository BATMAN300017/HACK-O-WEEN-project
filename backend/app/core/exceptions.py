from typing import Optional, Any, Dict
from fastapi import HTTPException, status

class SentinelFlowException(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class EntityNotFoundException(SentinelFlowException):
    pass

class UnauthorizedActionException(SentinelFlowException):
    pass

class ValidationException(SentinelFlowException):
    pass

class IdempotencyConflictException(SentinelFlowException):
    pass

class InsufficientDataException(SentinelFlowException):
    pass

def map_exception_to_http(exc: SentinelFlowException) -> HTTPException:
    if isinstance(exc, EntityNotFoundException):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    elif isinstance(exc, UnauthorizedActionException):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message)
    elif isinstance(exc, IdempotencyConflictException):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    elif isinstance(exc, InsufficientDataException):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
