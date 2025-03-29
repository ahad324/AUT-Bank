from typing import Dict, List, Set
from app.core.exceptions import CustomHTTPException
from fastapi import Depends, status
from app.core.auth import get_current_admin
from app.models.admin import Admin

# Define permissions as constants for clarity and reusability
PERMISSION_REGISTER_ADMIN = "admin:register"
PERMISSION_VIEW_ALL_ADMINS = "admin:view_all"
PERMISSION_VIEW_ADMIN_DETAILS = "admin:view_details"

PERMISSION_APPROVE_LOAN = "loan:approve"
PERMISSION_VIEW_ALL_LOANS = "loan:view_all"
PERMISSION_VIEW_USER_LOANS = "loan:view_user"
PERMISSION_VIEW_LOAN_DETAILS = "loan:view_details"

PERMISSION_VIEW_ALL_TRANSACTIONS = "transaction:view_all"
PERMISSION_VIEW_USER_TRANSACTIONS = "transaction:view_user"
PERMISSION_VIEW_TRANSACTION_DETAILS = "transaction:view_details"

PERMISSION_APPROVE_USER = "user:approve"
PERMISSION_VIEW_ALL_USERS = "user:view_all"
PERMISSION_VIEW_USER_DETAILS = "user:view_details"

# Role-based permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "SuperAdmin": {
        PERMISSION_REGISTER_ADMIN,
        PERMISSION_VIEW_ALL_ADMINS,
        PERMISSION_VIEW_ADMIN_DETAILS,
        PERMISSION_APPROVE_LOAN,
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_USER_LOANS,
        PERMISSION_VIEW_LOAN_DETAILS,
        PERMISSION_VIEW_ALL_TRANSACTIONS,
        PERMISSION_VIEW_USER_TRANSACTIONS,
        PERMISSION_VIEW_TRANSACTION_DETAILS,
        PERMISSION_APPROVE_USER,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS,
    },
    "Manager": {
        PERMISSION_APPROVE_LOAN,
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_USER_LOANS,
        PERMISSION_VIEW_LOAN_DETAILS,
        PERMISSION_VIEW_ALL_TRANSACTIONS,
        PERMISSION_VIEW_USER_TRANSACTIONS,
        PERMISSION_VIEW_TRANSACTION_DETAILS,
        PERMISSION_APPROVE_USER,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS
    },
    "Auditor": {
        PERMISSION_VIEW_ALL_LOANS,
        PERMISSION_VIEW_USER_LOANS,
        PERMISSION_VIEW_LOAN_DETAILS,
        PERMISSION_VIEW_ALL_TRANSACTIONS,
        PERMISSION_VIEW_USER_TRANSACTIONS,
        PERMISSION_VIEW_TRANSACTION_DETAILS,
        PERMISSION_VIEW_ALL_USERS,
        PERMISSION_VIEW_USER_DETAILS
    }
}

def require_permission(permission: str):
    """
    A dependency function to check if the current admin has the required permission.
    """
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

# Helper function to check multiple permissions (optional, for future use)
def has_permissions(role: str, required_permissions: List[str]) -> bool:
    if role not in ROLE_PERMISSIONS:
        return False
    role_permissions = ROLE_PERMISSIONS[role]
    return all(perm in role_permissions for perm in required_permissions)