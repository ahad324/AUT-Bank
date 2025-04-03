from pydantic import BaseModel
from typing import Union, List


class RoleCreate(BaseModel):
    RoleName: str
    Description: str | None = None


class PermissionCreate(BaseModel):
    PermissionName: str
    Description: str | None = None


class RolePermissionCreate(BaseModel):
    RoleID: int
    PermissionID: Union[int, List[int]]
