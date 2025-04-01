from pydantic import BaseModel, ConfigDict, constr
from datetime import date
from typing import Optional

class CardCreate(BaseModel):
    CardNumber: constr(min_length=16, max_length=16, pattern=r"^\d{16}$")  # type: ignore
    Pin: constr(min_length=4, max_length=4, pattern=r"^\d{4}$")  # type: ignore
    ExpirationDate: date

class CardResponse(BaseModel):
    CardID: int
    UserID: int
    CardNumber: str
    ExpirationDate: str
    Status: str
    CreatedAt: str
    model_config = ConfigDict(from_attributes=True)