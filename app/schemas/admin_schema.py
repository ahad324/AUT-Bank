from pydantic import BaseModel, EmailStr, constr, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum


class AdminCreate(BaseModel):
    Username: constr(min_length=3, max_length=50)  # type: ignore
    Email: EmailStr
    Password: constr(min_length=8, max_length=255)  # type: ignore # Enforce min 8 characters
    RoleID: int


class AdminLogin(BaseModel):
    Email: EmailStr
    Password: constr(min_length=8, max_length=255)  # type: ignore # Enforce min 8 characters


class RoleData(BaseModel):
    RoleID: int
    RoleName: str
    Description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class PermissionData(BaseModel):
    PermissionID: int
    PermissionName: str
    Description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AdminUpdate(BaseModel):
    Username: Optional[constr(min_length=3, max_length=50)] = None  # type: ignore
    Email: Optional[EmailStr] = None
    model_config = ConfigDict(from_attributes=True)


class OtherAdminUpdate(BaseModel):
    Username: Optional[constr(min_length=3, max_length=50)] = None  # type: ignore
    Email: Optional[EmailStr] = None
    RoleID: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AdminPasswordUpdate(BaseModel):
    CurrentPassword: constr(min_length=8, max_length=255)  # type: ignore
    NewPassword: constr(min_length=8, max_length=255)  # type: ignore


class AdminResponseData(BaseModel):
    AdminID: int
    Username: str
    Email: EmailStr
    RoleID: int
    CreatedAt: datetime
    LastLogin: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AdminLoginResponseData(BaseModel):
    AdminID: int
    Username: str
    Email: EmailStr
    Role: RoleData
    Permissions: List[PermissionData]
    LastLogin: Optional[str] = None
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
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
