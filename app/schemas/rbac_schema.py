from pydantic import BaseModel
from typing import Optional, Union, List


class RoleCreate(BaseModel):
    RoleName: str
    Description: str | None = None


class PermissionCreate(BaseModel):
    PermissionName: str
    Description: str | None = None


class RolePermissionCreate(BaseModel):
    RoleID: int
    PermissionID: Union[int, List[int]]


class RoleUpdate(BaseModel):
    RoleName: Optional[str] = None
    Description: Optional[str] = None


class PermissionUpdate(BaseModel):
    PermissionName: Optional[str] = None
    Description: Optional[str] = None


class RolePermissionRemove(BaseModel):
    RoleID: int
    PermissionID: Union[
        int, List[int]
    ]  # Supports removing single or multiple permissions
