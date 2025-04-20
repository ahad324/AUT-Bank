# app/controllers/rbac.py
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException
from app.models.admin import Admin
from app.models.rbac import Role, Permission, RolePermission
from app.schemas.rbac_schema import (
    PermissionUpdate,
    RoleCreate,
    PermissionCreate,
    RolePermissionCreate,
    RolePermissionRemove,
    RoleUpdate,
)
from app.core.responses import success_response
from typing import Union, List


def create_role(role_input: Union[RoleCreate, List[RoleCreate]], db: Session):
    # Normalize input to a list
    roles_to_create = [role_input] if isinstance(role_input, RoleCreate) else role_input
    if not roles_to_create:
        raise CustomHTTPException(status_code=400, message="No roles provided")

    new_roles = []
    existing_roles = []
    role_names = {role.RoleName for role in roles_to_create}

    # Check for existing roles
    existing = db.query(Role).filter(Role.RoleName.in_(role_names)).all()
    existing_names = {r.RoleName for r in existing}

    for role in roles_to_create:
        if role.RoleName in existing_names:
            existing_roles.append(role.RoleName)
        else:
            new_roles.append(Role(**role.model_dump()))

    if not new_roles:
        raise CustomHTTPException(
            status_code=400, message="All provided roles already exist"
        )

    try:
        db.add_all(new_roles)
        db.commit()
        for role in new_roles:
            db.refresh(role)
        return success_response(
            message=f"Created {len(new_roles)} role(s) successfully",
            data={
                "created_roles": [
                    {"RoleID": r.RoleID, "RoleName": r.RoleName} for r in new_roles
                ],
                "skipped_roles": existing_roles,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to create roles", details={"error": str(e)}
        )


def list_roles(db: Session):
    roles = db.query(Role).all()

    return success_response(
        message="Roles retrieved",
        data={
            "items": [
                {
                    "RoleID": r.RoleID,
                    "RoleName": r.RoleName,
                    "Description": r.Description,
                }
                for r in roles
            ]
        },
    )


def create_permission(
    perm_input: Union[PermissionCreate, List[PermissionCreate]], db: Session
):
    # Normalize input to a list
    perms_to_create = (
        [perm_input] if isinstance(perm_input, PermissionCreate) else perm_input
    )
    if not perms_to_create:
        raise CustomHTTPException(status_code=400, message="No permissions provided")

    new_perms = []
    existing_perms = []
    perm_names = {perm.PermissionName for perm in perms_to_create}

    # Check for existing permissions
    existing = (
        db.query(Permission).filter(Permission.PermissionName.in_(perm_names)).all()
    )
    existing_names = {p.PermissionName for p in existing}

    for perm in perms_to_create:
        if perm.PermissionName in existing_names:
            existing_perms.append(perm.PermissionName)
        else:
            new_perms.append(Permission(**perm.model_dump()))

    if not new_perms:
        raise CustomHTTPException(
            status_code=400, message="All provided permissions already exist"
        )

    try:
        db.add_all(new_perms)
        db.commit()
        for perm in new_perms:
            db.refresh(perm)
        return success_response(
            message=f"Created {len(new_perms)} permission(s) successfully",
            data={
                "items": [
                    {"PermissionID": p.PermissionID, "PermissionName": p.PermissionName}
                    for p in new_perms
                ],
                "skipped_permissions": existing_perms,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500,
            message="Failed to create permissions",
            details={"error": str(e)},
        )


def list_permissions(db: Session):
    perms = db.query(Permission).all()
    return success_response(
        message="Permissions retrieved",
        data={
            "items": [
                {
                    "PermissionID": p.PermissionID,
                    "PermissionName": p.PermissionName,
                    "Description": p.Description,
                }
                for p in perms
            ]
        },
    )


def assign_permissions_to_role(rp: RolePermissionCreate, db: Session):
    role = db.query(Role).filter(Role.RoleID == rp.RoleID).first()
    if not role:
        raise CustomHTTPException(status_code=404, message="Role not found")

    # Normalize PermissionID to a list
    permission_ids = (
        [rp.PermissionID] if isinstance(rp.PermissionID, int) else rp.PermissionID
    )
    if not permission_ids:
        raise CustomHTTPException(status_code=400, message="No permissions provided")

    invalid_permissions = []
    existing_assignments = []
    new_role_permissions = []

    for perm_id in permission_ids:
        permission = (
            db.query(Permission).filter(Permission.PermissionID == perm_id).first()
        )
        if not permission:
            invalid_permissions.append(perm_id)
        elif (
            db.query(RolePermission)
            .filter(
                RolePermission.RoleID == rp.RoleID,
                RolePermission.PermissionID == perm_id,
            )
            .first()
        ):
            existing_assignments.append(perm_id)
        else:
            new_role_permissions.append(
                RolePermission(RoleID=rp.RoleID, PermissionID=perm_id)
            )

    if invalid_permissions:
        raise CustomHTTPException(
            status_code=404,
            message=f"Permissions not found: {', '.join(map(str, invalid_permissions))}",
        )

    if not new_role_permissions:
        raise CustomHTTPException(
            status_code=400,
            message=(
                "All provided permissions are already assigned to the role"
                if existing_assignments
                else "No valid permissions provided"
            ),
        )

    try:
        db.add_all(new_role_permissions)
        db.commit()
        assigned_count = len(new_role_permissions)
        return success_response(
            message=f"Assigned {assigned_count} permission(s) to role successfully",
            data={
                "RoleID": rp.RoleID,
                "AssignedPermissionIDs": [
                    rp.PermissionID for rp in new_role_permissions
                ],
                "SkippedPermissionIDs": existing_assignments,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500,
            message="Failed to assign permissions",
            details={"error": str(e)},
        )


def update_role(role_id: int, role_update: RoleUpdate, db: Session):
    role = db.query(Role).filter(Role.RoleID == role_id).first()
    if not role:
        raise CustomHTTPException(status_code=404, message="Role not found")

    update_data = role_update.model_dump(exclude_unset=True)
    if "RoleName" in update_data and update_data["RoleName"] != role.RoleName:
        if db.query(Role).filter(Role.RoleName == update_data["RoleName"]).first():
            raise CustomHTTPException(
                status_code=400, message="Role name already exists"
            )

    for key, value in update_data.items():
        setattr(role, key, value)

    try:
        db.commit()
        db.refresh(role)
        return success_response(
            message="Role updated successfully",
            data={
                "RoleID": role.RoleID,
                "RoleName": role.RoleName,
                "Description": role.Description,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to update role", details={"error": str(e)}
        )


def delete_role(role_id: int, db: Session):
    role = db.query(Role).filter(Role.RoleID == role_id).first()
    if not role:
        raise CustomHTTPException(status_code=404, message="Role not found")

    # Check if role is assigned to admins
    if db.query(Admin).filter(Admin.RoleID == role_id).count() > 0:
        raise CustomHTTPException(
            status_code=400, message="Cannot delete role assigned to admins"
        )

    try:
        db.delete(role)
        db.commit()
        return success_response(
            message="Role deleted successfully", data={"RoleID": role_id}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500, message="Failed to delete role", details={"error": str(e)}
        )


def update_permission(permission_id: int, perm_update: PermissionUpdate, db: Session):
    permission = (
        db.query(Permission).filter(Permission.PermissionID == permission_id).first()
    )
    if not permission:
        raise CustomHTTPException(status_code=404, message="Permission not found")

    update_data = perm_update.model_dump(exclude_unset=True)
    if (
        "PermissionName" in update_data
        and update_data["PermissionName"] != permission.PermissionName
    ):
        if (
            db.query(Permission)
            .filter(Permission.PermissionName == update_data["PermissionName"])
            .first()
        ):
            raise CustomHTTPException(
                status_code=400, message="Permission name already exists"
            )

    for key, value in update_data.items():
        setattr(permission, key, value)

    try:
        db.commit()
        db.refresh(permission)
        return success_response(
            message="Permission updated successfully",
            data={
                "PermissionID": permission.PermissionID,
                "PermissionName": permission.PermissionName,
                "Description": permission.Description,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500,
            message="Failed to update permission",
            details={"error": str(e)},
        )


def delete_permission(permission_id: int, db: Session):
    permission = (
        db.query(Permission).filter(Permission.PermissionID == permission_id).first()
    )
    if not permission:
        raise CustomHTTPException(status_code=404, message="Permission not found")

    # Check if permission is assigned to roles
    if (
        db.query(RolePermission)
        .filter(RolePermission.PermissionID == permission_id)
        .count()
        > 0
    ):
        raise CustomHTTPException(
            status_code=400, message="Cannot delete permission assigned to roles"
        )

    try:
        db.delete(permission)
        db.commit()
        return success_response(
            message="Permission deleted successfully",
            data={"PermissionID": permission_id},
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500,
            message="Failed to delete permission",
            details={"error": str(e)},
        )


def remove_permissions_from_role(rp_remove: RolePermissionRemove, db: Session):
    role = db.query(Role).filter(Role.RoleID == rp_remove.RoleID).first()
    if not role:
        raise CustomHTTPException(status_code=404, message="Role not found")

    permission_ids = (
        [rp_remove.PermissionID]
        if isinstance(rp_remove.PermissionID, int)
        else rp_remove.PermissionID
    )
    if not permission_ids:
        raise CustomHTTPException(status_code=400, message="No permissions provided")

    invalid_permissions = []
    not_assigned_permissions = []
    role_permissions_to_remove = []

    for perm_id in permission_ids:
        permission = (
            db.query(Permission).filter(Permission.PermissionID == perm_id).first()
        )
        if not permission:
            invalid_permissions.append(perm_id)
        else:
            rp = (
                db.query(RolePermission)
                .filter(
                    RolePermission.RoleID == rp_remove.RoleID,
                    RolePermission.PermissionID == perm_id,
                )
                .first()
            )
            if not rp:
                not_assigned_permissions.append(perm_id)
            else:
                role_permissions_to_remove.append(rp)

    if invalid_permissions:
        raise CustomHTTPException(
            status_code=404,
            message=f"Permissions not found: {', '.join(map(str, invalid_permissions))}",
        )

    if not role_permissions_to_remove:
        raise CustomHTTPException(
            status_code=400,
            message=(
                "No valid permissions to remove"
                if not_assigned_permissions
                else "All provided permissions are not assigned to the role"
            ),
            details={"not_assigned": not_assigned_permissions},
        )

    try:
        for rp in role_permissions_to_remove:
            db.delete(rp)
        db.commit()
        return success_response(
            message=f"Removed {len(role_permissions_to_remove)} permission(s) from role successfully",
            data={
                "RoleID": rp_remove.RoleID,
                "RemovedPermissionIDs": [
                    rp.PermissionID for rp in role_permissions_to_remove
                ],
                "SkippedPermissionIDs": not_assigned_permissions,
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=500,
            message="Failed to remove permissions",
            details={"error": str(e)},
        )


# List permissions for a specific role
def list_role_permissions(role_id: int, db: Session):
    role = db.query(Role).filter(Role.RoleID == role_id).first()
    if not role:
        raise CustomHTTPException(status_code=404, message="Role not found")

    permissions = (
        db.query(Permission)
        .join(RolePermission, RolePermission.PermissionID == Permission.PermissionID)
        .filter(RolePermission.RoleID == role_id)
        .all()
    )
    return success_response(
        message="Role permissions retrieved",
        data={
            "RoleID": role_id,
            "RoleName": role.RoleName,
            "permissions": [
                {
                    "PermissionID": p.PermissionID,
                    "PermissionName": p.PermissionName,
                    "Description": p.Description,
                }
                for p in permissions
            ],
        },
    )
