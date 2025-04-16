from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, constr
from decimal import Decimal
from typing import Optional


class TransferCreate(BaseModel):
    cnic: Optional[constr(pattern=r"^\d{5}-\d{7}-\d{1}$")] = None  # type: ignore
    username: Optional[constr(min_length=3, max_length=50)] = None  # type: ignore
    email: Optional[EmailStr] = None
    Amount: Decimal
    Description: Optional[str] = None

    @field_validator("cnic", "username", "email")
    @classmethod
    def ensure_exactly_one_identifier(cls, v, info):
        values = info.data
        identifiers = ["cnic", "username", "email"]
        provided = [
            k
            for k in identifiers
            if values.get(k) is not None or (info.field_name == k and v is not None)
        ]
        if len(provided) != 1:
            raise ValueError("Exactly one of CNIC, Username, or Email must be provided")
        return v


class TransferResponse(BaseModel):
    TransferID: int
    SenderID: int
    ReceiverID: int
    Amount: float
    ReferenceNumber: str
    Status: str
    Description: Optional[str]
    Timestamp: datetime
    model_config = ConfigDict(from_attributes=True)
