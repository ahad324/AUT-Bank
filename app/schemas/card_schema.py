from pydantic import BaseModel, ConfigDict, constr, validator
from datetime import date, datetime
from typing import Optional


class CardCreate(BaseModel):
    CardNumber: constr(min_length=16, max_length=16, pattern=r"^\d{16}$")  # type: ignore
    Pin: constr(min_length=4, max_length=4, pattern=r"^\d{4}$")  # type: ignore
    ExpirationDate: date


class CardUpdate(BaseModel):
    Pin: Optional[constr(min_length=4, max_length=4, pattern=r"^\d{4}$")] = None  # type: ignore
    Status: Optional[str] = None  # "Active", "Inactive", "Blocked"

    @validator("Status")
    def validate_status(cls, v):
        if v and v not in ["Active", "Inactive", "Blocked"]:
            raise ValueError("Status must be 'Active', 'Inactive', or 'Blocked'")
        return v


class CardResponse(BaseModel):
    CardID: int
    UserID: int
    CardNumber: str
    ExpirationDate: date
    Status: str
    CreatedAt: datetime
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),  # Handle date objects
        },
    )
