from pydantic import BaseModel, ConfigDict
from typing import TypeVar, Optional, Dict, Any
from datetime import datetime, date

T = TypeVar('T')

class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.strftime('%Y-%m-%d')
        },
        from_attributes=True
    )

class PaginatedResponse(BaseResponse):
    page: int
    per_page: int
    total_items: int
    total_pages: int