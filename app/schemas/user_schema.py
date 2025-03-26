from pydantic import BaseModel, EmailStr, constr
from datetime import datetime

class UserCreate(BaseModel):
    Username: constr(min_length=3, max_length=50) # type: ignore
    CNIC: constr(min_length=13, max_length=15) # type: ignore
    Email: EmailStr
    Password: str
    AccountType: str
    DateOfBirth: datetime

class UserResponse(BaseModel):
    UserID: int
    Username: str
    Email: EmailStr
    AccountType: str
    Balance: float
    CreatedAt: datetime

    class Config:
        from_attributes = True
