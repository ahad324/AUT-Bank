from pydantic import BaseModel, EmailStr, constr, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class AdminCreate(BaseModel):
    Username: constr(min_length=3, max_length=50)  # type: ignore
    Email: EmailStr
    Password: str
    RoleID: int


class AdminLogin(BaseModel):
    Email: EmailStr
    Password: str


class AdminResponseData(BaseModel):
    AdminID: int
    Username: str
    Email: EmailStr
    RoleID: int
    CreatedAt: datetime
    LastLogin: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AdminSortBy(str, Enum):
    admin_id = "AdminID"
    username = "Username"
    email = "Email"
    role = "RoleID"
    created_at = "CreatedAt"
    last_login = "LastLogin"


class AdminOrder(str, Enum):
    asc = "asc"
    desc = "desc"
