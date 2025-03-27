from pydantic import BaseModel, ConfigDict
from typing import Generic, TypeVar, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

T = TypeVar('T')

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.strftime('%Y-%m-%d')
        }
    )

class PaginatedResponse(BaseResponse):
    page: int
    per_page: int
    total_items: int
    total_pages: int