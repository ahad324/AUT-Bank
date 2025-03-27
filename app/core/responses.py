from fastapi import status
from typing import Any, Dict, Optional
from .schemas import BaseResponse

def success_response(
    message: str,
    data: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_200_OK
) -> Dict[str, Any]:
    return BaseResponse(
        success=True,
        message=message,
        data=data,
    ).model_dump()

def error_response(
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    return BaseResponse(
        success=False,
        message=message,
        data=details or {},
    ).model_dump()