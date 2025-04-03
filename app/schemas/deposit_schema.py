from datetime import datetime
from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import Optional


class DepositCreate(BaseModel):
    Amount: Decimal
    Description: Optional[str] = None


class DepositResponse(BaseModel):
    DepositID: int
    UserID: int
    AdminID: int
    Amount: float
    ReferenceNumber: str
    Status: str
    Description: Optional[str]
    Timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
