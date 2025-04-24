import re
from pydantic import BaseModel, EmailStr, constr, field_validator, ConfigDict
from datetime import date, datetime
from typing import Optional
from enum import Enum

from decimal import Decimal


class UserCreate(BaseModel):
    Username: constr(min_length=3, max_length=50)  # type: ignore
    FirstName: constr(max_length=50) = ""  # type: ignore
    LastName: constr(max_length=50) = ""  # type: ignore
    StreetAddress: Optional[constr(max_length=255)] = None  # type: ignore
    City: Optional[constr(max_length=50)] = None  # type: ignore
    State: Optional[constr(max_length=50)] = None  # type: ignore
    Country: Optional[constr(max_length=50)] = None  # type: ignore
    PostalCode: Optional[constr(max_length=20)] = None  # type: ignore
    PhoneNumber: Optional[constr(max_length=20)] = None  # type: ignore
    CNIC: constr(pattern=r"^\d{5}-\d{7}-\d{1}$")  # type: ignore
    Email: EmailStr
    Password: constr(min_length=8, max_length=255)  # type: ignore
    IsActive: bool = False
    AccountType: str
    DateOfBirth: date

    @field_validator("AccountType")
    def validate_account_type(cls, v):
        if v not in ("Savings", "Current"):
            raise ValueError("AccountType must be either 'Savings' or 'Current'")
        return v

    @field_validator("CNIC")
    def validate_cnic_format(cls, v):
        if not (v[5] == "-" and v[13] == "-" and len(v) == 15):
            raise ValueError("CNIC must be in format XXXXX-XXXXXXX-X")
        return v


class UniquenessCheck(BaseModel):
    field: str
    value: str

    @field_validator("field")
    @classmethod
    def validate_field(cls, v):
        allowed_fields = {"Email", "CNIC", "Username"}
        if v not in allowed_fields:
            raise ValueError("Field must be Email, CNIC, or Username")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v, values):
        field = values.data.get("field")  # Access 'field' from values.data

        if field == "Email":
            if not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
                raise ValueError("Invalid email format")
        elif field == "CNIC":
            if not re.match(r"^\d{5}-\d{7}-\d{1}$", v):
                raise ValueError("CNIC must be in format XXXXX-XXXXXXX-X")
        elif field == "Username":
            if not (3 <= len(v) <= 50):
                raise ValueError("Username must be between 3 and 50 characters")

        return v


class UserUpdate(BaseModel):
    Username: Optional[constr(min_length=3, max_length=50)] = None  # type: ignore
    FirstName: Optional[constr(max_length=50)] = None  # type: ignore
    LastName: Optional[constr(max_length=50)] = None  # type: ignore
    StreetAddress: Optional[constr(max_length=255)] = None  # type: ignore
    City: Optional[constr(max_length=50)] = None  # type: ignore
    State: Optional[constr(max_length=50)] = None  # type: ignore
    Country: Optional[constr(max_length=50)] = None  # type: ignore
    PostalCode: Optional[constr(max_length=20)] = None  # type: ignore
    PhoneNumber: Optional[constr(max_length=20)] = None  # type: ignore
    Password: Optional[constr(min_length=8, max_length=255)] = None  # type: ignore # Added for admin updates
    Email: Optional[EmailStr] = None
    IsActive: Optional[bool] = None  # Admin-only field, added for flexibility
    model_config = ConfigDict(from_attributes=True)


# Dedicated schema for user password update
class UserPasswordUpdate(BaseModel):
    CurrentPassword: constr(min_length=8, max_length=255)  # type: ignore
    NewPassword: constr(min_length=8, max_length=255)  # type: ignore


class UserLogin(BaseModel):
    login_id: str  # Can be either email or username
    Password: constr(min_length=8, max_length=255)  # type: ignore

    @field_validator("login_id")
    def validate_login_id(cls, v):
        if not v:
            raise ValueError("Login ID cannot be empty")
        return v


class UserResponseData(BaseModel):
    UserID: int
    Username: str
    FirstName: str
    LastName: str
    StreetAddress: Optional[str] = None
    City: Optional[str] = None
    State: Optional[str] = None
    Country: Optional[str] = None
    PostalCode: Optional[str] = None
    PhoneNumber: Optional[str] = None
    CNIC: str
    Email: str
    AccountType: str
    Balance: float
    IsActive: bool
    DateOfBirth: date  # Accept date object
    CreatedAt: datetime  # Accept datetime object
    LastLogin: Optional[datetime] = None  # Accept datetime object or None
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "bearer"

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            Decimal: lambda v: float(v),
        },
    )


class LoginResponseData(BaseModel):
    UserID: int
    Username: str
    Email: EmailStr
    AccountType: str
    Balance: float
    last_login: Optional[str] = None
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat() if v else None,
        },
    )


class EmailVerificationType(str, Enum):
    otp = "otp"
    message = "message"


class EmailVerificationRequest(BaseModel):
    email: EmailStr
    content: constr(min_length=1, max_length=1000)  # type: ignore
    type: EmailVerificationType
    secret_code: constr(min_length=1, max_length=100)  # type: ignore

    @field_validator("content")
    def validate_content(cls, v, values):
        if "type" in values.data and values.data["type"] == EmailVerificationType.otp:
            if not re.match(r"^\d{4,6}$", v):
                raise ValueError("OTP must be a 4-6 digit number")
        return v


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
