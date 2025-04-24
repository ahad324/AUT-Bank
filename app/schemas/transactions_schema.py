from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class TransactionResponse(BaseModel):
    TransactionID: int
    UserID: int
    Username: str
    Amount: float
    TransactionType: str
    Status: str
    Description: Optional[str] = None
    CreatedAt: Optional[datetime] = None
    UpdatedAt: Optional[datetime] = None
    ReceiverID: Optional[int] = None
    ReceiverUsername: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        },
    )
