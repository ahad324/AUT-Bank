from pydantic import BaseModel, EmailStr, constr, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional
from app.core.schemas import BaseResponse

class AdminRole(str, Enum):
    SUPERADMIN = "SuperAdmin"
    MANAGER = "Manager"
    AUDITOR = "Auditor"

class AdminCreate(BaseModel):
    Username: constr(min_length=3, max_length=50)  # type: ignore
    Email: EmailStr
    Password: str
    Role: AdminRole

class AdminLogin(BaseModel):
    Email: EmailStr
    Password: str

class AdminResponseData(BaseModel):
    AdminID: int
    Username: str
    Email: EmailStr
    Role: str
    CreatedAt: datetime
    LastLogin: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AdminSortBy(str, Enum):
    admin_id = "AdminID"
    username = "Username"
    email = "Email"
    role = "Role"
    created_at = "CreatedAt"
    last_login = "LastLogin"

class AdminOrder(str, Enum):
    asc = "asc"
    desc = "desc"   