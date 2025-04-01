from typing import Dict, List, Set
from app.core.exceptions import CustomHTTPException
from fastapi import Depends, status
from app.core.auth import get_current_admin
from app.models.admin import Admin

# Define permissions as constants
PERMISSION_REGISTER_ADMIN = "admin:register"
PERMISSION_VIEW_ALL_ADMINS = "admin:view_all"
PERMISSION_VIEW_ADMIN_DETAILS = "admin:view_details"

PERMISSION_APPROVE_LOAN = "loan:approve"
PERMISSION_VIEW_ALL_LOANS = "loan:view_all"

PERMISSION_VIEW_ALL_TRANSACTIONS = "transaction:view_all"

PERMISSION_VIEW_ALL_TRANSFERS = "transfer:view_all"
PERMISSION_VIEW_USER_TRANSFERS = "transfer:view_user"
PERMISSION_VIEW_TRANSFER_DETAILS = "transfer:view_details"

PERMISSION_VIEW_ALL_DEPOSITS = "deposit:view_all"
PERMISSION_VIEW_USER_DEPOSITS = "deposit:view_user"
PERMISSION_VIEW_DEPOSIT_DETAILS = "deposit:view_details"
PERMISSION_MANAGE_DEPOSITS = "deposit:manage"

PERMISSION_VIEW_ALL_WITHDRAWALS = "withdrawal:view_all"
PERMISSION_VIEW_USER_WITHDRAWALS = "withdrawal:view_user"
PERMISSION_VIEW_WITHDRAWAL_DETAILS = "withdrawal:view_details"

PERMISSION_APPROVE_USER = "user:approve"
PERMISSION_VIEW_ALL_USERS = "user:view_all"
PERMISSION_VIEW_USER_DETAILS = "user:view_details"
PERMISSION_UPDATE_USER = "user:update_details"
PERMISSION_DELETE_USER = "user:delete_details"

# Role-based permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "SuperAdmin": {
        PERMISSION_REGISTER_ADMIN,
        PERMISSION_VIEW_ALL_ADMINS,
        PERMISSION_VIEW_ADMIN_DETAILS,
        PERMISSION_APPROVE_LOAN,
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_ALL_TRANSACTIONS,
        PERMISSION_VIEW_ALL_TRANSFERS,
        PERMISSION_VIEW_USER_TRANSFERS,
        PERMISSION_VIEW_TRANSFER_DETAILS,
        PERMISSION_VIEW_ALL_DEPOSITS,
        PERMISSION_VIEW_USER_DEPOSITS,
        PERMISSION_VIEW_DEPOSIT_DETAILS,
        PERMISSION_MANAGE_DEPOSITS,
        PERMISSION_VIEW_ALL_WITHDRAWALS,
        PERMISSION_VIEW_USER_WITHDRAWALS,
        PERMISSION_VIEW_WITHDRAWAL_DETAILS,
        PERMISSION_APPROVE_USER,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS,
        PERMISSION_UPDATE_USER,
        PERMISSION_DELETE_USER
    },
    "Manager": {
        PERMISSION_APPROVE_LOAN,
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_ALL_TRANSFERS,
        PERMISSION_VIEW_USER_TRANSFERS,
        PERMISSION_VIEW_TRANSFER_DETAILS,
        PERMISSION_VIEW_ALL_DEPOSITS,
        PERMISSION_VIEW_USER_DEPOSITS,
        PERMISSION_VIEW_DEPOSIT_DETAILS,
        PERMISSION_MANAGE_DEPOSITS,
        PERMISSION_VIEW_ALL_WITHDRAWALS,
        PERMISSION_VIEW_USER_WITHDRAWALS,
        PERMISSION_VIEW_WITHDRAWAL_DETAILS,
        PERMISSION_APPROVE_USER,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS,
        PERMISSION_UPDATE_USER,
        PERMISSION_DELETE_USER
    },
    "Auditor": {
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_ALL_TRANSFERS,
        PERMISSION_VIEW_USER_TRANSFERS,
        PERMISSION_VIEW_TRANSFER_DETAILS,
        PERMISSION_VIEW_ALL_DEPOSITS,
        PERMISSION_VIEW_USER_DEPOSITS,
        PERMISSION_VIEW_DEPOSIT_DETAILS,
        PERMISSION_VIEW_ALL_WITHDRAWALS,
        PERMISSION_VIEW_USER_WITHDRAWALS,
        PERMISSION_VIEW_WITHDRAWAL_DETAILS,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS
    }
}

def require_permission(permission: str):
    def check_permission(current_admin: Admin = Depends(get_current_admin)):
        role = current_admin.Role
        if role not in ROLE_PERMISSIONS:
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                message=f"Role '{role}' is not recognized",
                details={}
            )
        
        if permission not in ROLE_PERMISSIONS[role]:
            raise CustomHTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                message=f"Permission '{permission}' denied for role '{role}'",
                details={}
            )
        
        return current_admin
    return check_permission

def has_permissions(role: str, required_permissions: List[str]) -> bool:
    if role not in ROLE_PERMISSIONS:
        return False
    role_permissions = ROLE_PERMISSIONS[role]
    return all(perm in role_permissions for perm in required_permissions)