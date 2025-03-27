from pydantic import BaseModel, EmailStr, constr, validator, ConfigDict
from datetime import date, datetime
from typing import Optional
from enum import Enum
from decimal import Decimal

class UserCreate(BaseModel):
    Username: constr(min_length=3, max_length=50)  # type: ignore
    FirstName: constr(max_length=50) = ''  # type: ignore
    LastName: constr(max_length=50) = ''  # type: ignore
    StreetAddress: Optional[constr(max_length=255)] = None  # type: ignore
    City: Optional[constr(max_length=50)] = None  # type: ignore
    State: Optional[constr(max_length=50)] = None  # type: ignore
    Country: Optional[constr(max_length=50)] = None  # type: ignore
    PostalCode: Optional[constr(max_length=20)] = None  # type: ignore
    PhoneNumber: Optional[constr(max_length=20)] = None  # type: ignore
    CNIC: constr(min_length=13, max_length=15)  # type: ignore
    Email: EmailStr
    Password: str
    AccountType: str
    DateOfBirth: date  # Using date type directly

    @validator('AccountType')
    def validate_account_type(cls, v):
        if v not in ('Savings', 'Current'):
            raise ValueError("AccountType must be either 'Savings' or 'Current'")
        return v

    @validator('CNIC')
    def validate_cnic_format(cls, v):
        if not (v[5] == '-' and v[13] == '-' and len(v) == 15):
            raise ValueError("CNIC must be in format XXXXX-XXXXXXX-X")
        return v
    
class UserLogin(BaseModel):
    login_id: str  # Can be either email or username
    Password: str
    
    @validator('login_id')
    def validate_login_id(cls, v):
        if not v:
            raise ValueError("Login ID cannot be empty")
        return v
class UserResponseData(BaseModel):
    UserID: int
    Username: str
    FirstName: str
    LastName: str
    Email: EmailStr
    AccountType: str
    Balance: Decimal
    DateOfBirth: date
    CreatedAt: datetime
    LastLogin: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class LoginResponseData(BaseModel):
    UserID: int
    Username: str
    Email: EmailStr
    AccountType: str
    last_login: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SortBy(str, Enum):
    user_id = "user_id"
    username = "username"
    email = "email"
    balance = "balance"
    created_at = "created_at"
    last_login = "last_login"

class Order(str, Enum):
    asc = "asc"
    desc = "desc"

class PaginationParams(BaseModel):
    page: int = 1  # Default to page 1
    per_page: int = 10  # Default to 10 items per page

class LoanFilterSortParams(BaseModel):
    status: Optional[str] = None  # e.g., "Pending", "Approved"
    sort_by: Optional[str] = "CreatedAt"  # e.g., "CreatedAt", "DueDate", "LoanAmount"
    order: Optional[str] = "desc"  # "asc" or "desc"