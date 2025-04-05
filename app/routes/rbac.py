# app/routes/rbac.py
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac import check_permission
from app.core.schemas import BaseResponse
from app.models.admin import Admin
from app.schemas.rbac_schema import (
    PermissionUpdate,
    RoleCreate,
    PermissionCreate,
    RolePermissionCreate,
    RolePermissionRemove,
    RoleUpdate,
)
from app.controllers.rbac_controller import (
    create_role,
    delete_permission,
    delete_role,
    list_role_permissions,
    list_roles,
    create_permission,
    list_permissions,
    assign_permissions_to_role,
    remove_permissions_from_role,
    update_permission,
    update_role,
)
from typing import Union, List
from app.core.rate_limiter import limiter
import os

router = APIRouter()


@router.post("/roles", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def create_role_route(
    request: Request,
    role_input: Union[RoleCreate, List[RoleCreate]],
    current_admin: Admin = Depends(check_permission("rbac:manage_roles")),
    db: Session = Depends(get_db),
):
    return create_role(role_input, db)


@router.get("/roles", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_roles_route(
    request: Request,
    current_admin: Admin = Depends(check_permission("rbac:view_roles")),
    db: Session = Depends(get_db),
):
    return list_roles(db)


@router.post("/permissions", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def create_permission_route(
    request: Request,
    perm_input: Union[PermissionCreate, List[PermissionCreate]],
    current_admin: Admin = Depends(check_permission("rbac:manage_permissions")),
    db: Session = Depends(get_db),
):
    return create_permission(perm_input, db)


@router.get("/permissions", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_permissions_route(
    request: Request,
    current_admin: Admin = Depends(check_permission("rbac:view_permissions")),
    db: Session = Depends(get_db),
):
    return list_permissions(db)


@router.post("/role-permissions", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def assign_permissions_to_role_route(
    request: Request,
    rp: RolePermissionCreate,
    current_admin: Admin = Depends(check_permission("rbac:manage_role_permissions")),
    db: Session = Depends(get_db),
):
    return assign_permissions_to_role(rp, db)


@router.delete("/role-permissions", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def remove_permissions_from_role_route(
    request: Request,
    rp_remove: RolePermissionRemove,
    current_admin: Admin = Depends(check_permission("rbac:manage_role_permissions")),
    db: Session = Depends(get_db),
):
    return remove_permissions_from_role(rp_remove, db)


@router.get("/roles/{role_id}/permissions", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_role_permissions_route(
    request: Request,
    role_id: int,
    current_admin: Admin = Depends(check_permission("rbac:view_roles")),
    db: Session = Depends(get_db),
):
    return list_role_permissions(role_id, db)


@router.put("/roles/{role_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def update_role_route(
    request: Request,
    role_id: int,
    role_update: RoleUpdate,
    current_admin: Admin = Depends(check_permission("rbac:manage_roles")),
    db: Session = Depends(get_db),
):
    return update_role(role_id, role_update, db)


@router.delete("/roles/{role_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def delete_role_route(
    request: Request,
    role_id: int,
    current_admin: Admin = Depends(check_permission("rbac:manage_roles")),
    db: Session = Depends(get_db),
):
    return delete_role(role_id, db)


@router.put("/permissions/{permission_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def update_permission_route(
    request: Request,
    permission_id: int,
    perm_update: PermissionUpdate,
    current_admin: Admin = Depends(check_permission("rbac:manage_permissions")),
    db: Session = Depends(get_db),
):
    return update_permission(permission_id, perm_update, db)


@router.delete("/permissions/{permission_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def delete_permission_route(
    request: Request,
    permission_id: int,
    current_admin: Admin = Depends(check_permission("rbac:manage_permissions")),
    db: Session = Depends(get_db),
):
    return delete_permission(permission_id, db)
