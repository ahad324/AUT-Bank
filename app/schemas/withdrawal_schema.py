from datetime import datetime
from pydantic import BaseModel, ConfigDict, constr
from decimal import Decimal
from typing import Optional


class WithdrawalCreate(BaseModel):
    CardNumber: constr(min_length=16, max_length=16, pattern=r"^\d{16}$")  # type: ignore
    Pin: constr(min_length=4, max_length=4, pattern=r"^\d{4}$")  # type: ignore
    Amount: Decimal


class WithdrawalResponse(BaseModel):
    WithdrawalID: int
    UserID: int
    CardID: int
    Amount: float
    ReferenceNumber: str
    Status: str
    Description: Optional[str]
    CreatedAt: datetime
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
        },
    )
