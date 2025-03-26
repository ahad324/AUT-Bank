from pydantic import BaseModel, EmailStr, constr, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional

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

class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    AdminID: int
    Username: str
    Email: EmailStr
    Role: str
    CreatedAt: datetime
    LastLogin: Optional[datetime] = None