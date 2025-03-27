from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from .responses import error_response

class CustomHTTPException(HTTPException):
    def __init__(
        self,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail=error_response(message, status_code, details)
        )

class DatabaseError(CustomHTTPException):
    def __init__(self, message: str):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, message)