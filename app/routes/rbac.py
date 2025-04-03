# app/routes/rbac.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import check_permission
from app.core.schemas import BaseResponse
from app.models.admin import Admin
from app.schemas.rbac_schema import RoleCreate, PermissionCreate, RolePermissionCreate
from app.controllers.rbac_controller import (
    create_role,
    list_roles,
    create_permission,
    list_permissions,
    assign_permissions_to_role,
)
from typing import Union, List

router = APIRouter()


@router.post("/roles", response_model=BaseResponse)
def create_role_route(
    role_input: Union[RoleCreate, List[RoleCreate]],
    current_admin: Admin = Depends(check_permission("rbac:manage_roles")),
    db: Session = Depends(get_db),
):
    return create_role(role_input, db)


@router.get("/roles", response_model=BaseResponse)
def list_roles_route(
    current_admin: Admin = Depends(check_permission("rbac:view_roles")),
    db: Session = Depends(get_db),
):
    return list_roles(db)


@router.post("/permissions", response_model=BaseResponse)
def create_permission_route(
    perm_input: Union[PermissionCreate, List[PermissionCreate]],
    current_admin: Admin = Depends(check_permission("rbac:manage_permissions")),
    db: Session = Depends(get_db),
):
    return create_permission(perm_input, db)


@router.get("/permissions", response_model=BaseResponse)
def list_permissions_route(
    current_admin: Admin = Depends(check_permission("rbac:view_permissions")),
    db: Session = Depends(get_db),
):
    return list_permissions(db)


@router.post("/role-permissions", response_model=BaseResponse)
def assign_permissions_to_role_route(
    rp: RolePermissionCreate,
    current_admin: Admin = Depends(check_permission("rbac:manage_role_permissions")),
    db: Session = Depends(get_db),
):
    return assign_permissions_to_role(rp, db)
