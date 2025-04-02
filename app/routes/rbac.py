from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import check_permission
from app.core.schemas import BaseResponse
from app.core.exceptions import CustomHTTPException
from app.models.admin import Admin
from app.models.rbac import PermissionCreate, Role, Permission, RoleCreate, RolePermission, RolePermissionCreate

router = APIRouter()

@router.post("/roles", response_model=BaseResponse)
def create_role(
    role: RoleCreate,
    current_admin: Admin = Depends(check_permission("rbac:manage_roles")),
    db: Session = Depends(get_db)
):
    if db.query(Role).filter(Role.RoleName == role.RoleName).first():
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Role already exists")
    new_role = Role(**role.model_dump())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return {"success": True, "message": "Role created successfully", "data": {"RoleID": new_role.RoleID}}

@router.get("/roles", response_model=BaseResponse)
def list_roles(
    current_admin: Admin = Depends(check_permission("rbac:view_roles")),
    db: Session = Depends(get_db)
):
    roles = db.query(Role).all()
    return {"success": True, "message": "Roles retrieved", "data": {"roles":[{"RoleID": r.RoleID, "RoleName": r.RoleName} for r in roles]}}

@router.post("/permissions", response_model=BaseResponse)
def create_permission(
    permission: PermissionCreate,
    current_admin: Admin = Depends(check_permission("rbac:manage_permissions")),
    db: Session = Depends(get_db)
):
    if db.query(Permission).filter(Permission.PermissionName == permission.PermissionName).first():
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Permission already exists")
    new_perm = Permission(**permission.model_dump())
    db.add(new_perm)
    db.commit()
    db.refresh(new_perm)
    return {"success": True, "message": "Permission created successfully", "data": {"PermissionID": new_perm.PermissionID}}

@router.get("/permissions", response_model=BaseResponse)
def list_permissions(
    current_admin: Admin = Depends(check_permission("rbac:view_permissions")),
    db: Session = Depends(get_db)
):
    perms = db.query(Permission).all()
    return {"success": True, "message": "Permissions retrieved", "data": {"permissions": [{"PermissionID": p.PermissionID, "PermissionName": p.PermissionName} for p in perms]}}

@router.post("/role-permissions", response_model=BaseResponse)
def assign_permission_to_role(
    rp: RolePermissionCreate,
    current_admin: Admin = Depends(check_permission("rbac:manage_role_permissions")),
    db: Session = Depends(get_db)
):
    if not db.query(Role).filter(Role.RoleID == rp.RoleID).first():
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Role not found")
    if not db.query(Permission).filter(Permission.PermissionID == rp.PermissionID).first():
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Permission not found")
    if db.query(RolePermission).filter(RolePermission.RoleID == rp.RoleID, RolePermission.PermissionID == rp.PermissionID).first():
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Permission already assigned to role")
    new_rp = RolePermission(**rp.model_dump())
    db.add(new_rp)
    db.commit()
    return {"success": True, "message": "Permission assigned to role successfully"}
