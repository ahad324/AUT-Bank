from fastapi import Depends, status
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException
from app.core.auth import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.rbac import Role, RolePermission, Permission


def check_permission(permission: str):
    def permission_checker(
        current_admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)
    ):
        # Fetch the role and its permissions
        role_permissions = (
            db.query(Permission.PermissionName)
            .join(
                RolePermission, RolePermission.PermissionID == Permission.PermissionID
            )
            .join(Role, Role.RoleID == RolePermission.RoleID)
            .filter(Role.RoleID == current_admin.RoleID)
            .all()
        )

        # Extract permission names as a list
        permissions = [rp.PermissionName for rp in role_permissions]

        if permission not in permissions:
            role_name = (
                db.query(Role.RoleName)
                .filter(Role.RoleID == current_admin.RoleID)
                .scalar()
            )
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                message=f"Permission '{permission}' denied for role '{role_name}'",
                details={},
            )
        return current_admin

    return permission_checker


def get_role_permissions(role_id: int, db: Session) -> set[str]:
    permissions = (
        db.query(Permission.PermissionName)
        .join(RolePermission, RolePermission.PermissionID == Permission.PermissionID)
        .filter(RolePermission.RoleID == role_id)
        .all()
    )
    return {p.PermissionName for p in permissions}


def has_permissions(role_id: int, required_permissions: list[str], db: Session) -> bool:
    role_permissions = get_role_permissions(role_id, db)
    return all(perm in role_permissions for perm in required_permissions)
