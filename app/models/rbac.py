from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base

class Role(Base):
    __tablename__ = "Roles"

    RoleID = Column(Integer, primary_key=True, index=True)
    RoleName = Column(String(50), unique=True, nullable=False)
    Description = Column(String(255), nullable=True)

class Permission(Base):
    __tablename__ = "Permissions"

    PermissionID = Column(Integer, primary_key=True, index=True)
    PermissionName = Column(String(100), unique=True, nullable=False)
    Description = Column(String(255), nullable=True)

class RolePermission(Base):
    __tablename__ = "RolePermissions"

    RolePermissionID = Column(Integer, primary_key=True, index=True)
    RoleID = Column(Integer, ForeignKey("Roles.RoleID", ondelete="CASCADE"), nullable=False)
    PermissionID = Column(Integer, ForeignKey("Permissions.PermissionID", ondelete="CASCADE"), nullable=False)
    
class RoleCreate(BaseModel):
    RoleName: str
    Description: str | None = None

class PermissionCreate(BaseModel):
    PermissionName: str
    Description: str | None = None

class RolePermissionCreate(BaseModel):
    RoleID: int
    PermissionID: int
