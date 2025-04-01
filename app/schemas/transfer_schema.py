from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from typing import Optional

class TransferCreate(BaseModel):
    ReceiverID: int
    Amount: Decimal
    Description: Optional[str] = None

class TransferResponse(BaseModel):
    TransferID: int
    SenderID: int
    ReceiverID: int
    Amount: float
    ReferenceNumber: str
    Status: str
    Description: Optional[str]
    Timestamp: str
    model_config = ConfigDict(from_attributes=True)