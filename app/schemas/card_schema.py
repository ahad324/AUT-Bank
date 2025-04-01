from pydantic import BaseModel, ConfigDict, constr
from datetime import date, datetime

class CardCreate(BaseModel):
    CardNumber: constr(min_length=16, max_length=16, pattern=r"^\d{16}$")  # type: ignore
    Pin: constr(min_length=4, max_length=4, pattern=r"^\d{4}$")  # type: ignore
    ExpirationDate: date

class CardPinUpdate(BaseModel):
    CardNumber: constr(min_length=16, max_length=16, pattern=r"^\d{16}$")  # type: ignore
    NewPin: constr(min_length=4, max_length=4, pattern=r"^\d{4}$")  # type: ignore
    
class CardResponse(BaseModel):
    CardID: int
    UserID: int
    CardNumber: str
    ExpirationDate: date
    Status: str
    CreatedAt: datetime
    model_config = ConfigDict(from_attributes=True)