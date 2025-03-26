from fastapi import status
from typing import Any, Dict, Optional
from pydantic import BaseModel

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    status_code: int = status.HTTP_200_OK

def success_response(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data or {},
        "status_code": status_code
    }

def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": details or {},
        "status_code": status_code
    }