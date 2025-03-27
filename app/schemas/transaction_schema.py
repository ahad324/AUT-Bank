from pydantic import BaseModel, ConfigDict, constr, PositiveFloat
from typing import Optional
from datetime import datetime

class TransactionCreate(BaseModel):
    ReceiverID: Optional[int] = None
    Amount: PositiveFloat
    TransactionType: constr(pattern="^(Deposit|Withdrawal|Transfer|Loan Repayment)$")  # type: ignore
    Description: Optional[constr(max_length=255)] = None  # type: ignore

class TransactionResponse(BaseModel):
    TransactionID: int
    SenderID: Optional[int] = None
    ReceiverID: Optional[int] = None
    Amount: float
    TransactionType: str
    ReferenceNumber: Optional[str] = None
    Status: str
    Description: Optional[str] = None
    Timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

class DepositRequest(BaseModel):
    Amount: PositiveFloat
    Description: Optional[constr(max_length=255)] = None  # type: ignore