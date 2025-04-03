from typing import Optional
from fastapi import status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone

# Schemas
from app.core.exceptions import CustomHTTPException
from app.core.schemas import PaginatedResponse
from app.models.loan import Loan
from app.models.user import User
from app.schemas.admin_schema import (
    AdminCreate,
    AdminLogin,
    AdminOrder,
    AdminResponseData,
    AdminSortBy,
)

# Models
from app.models.admin import Admin

# Core
from app.core.auth import create_access_token, create_refresh_token
from app.core.responses import success_response, error_response
from app.schemas.user_schema import Order, SortBy, UserResponseData, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_admin(admin: AdminCreate, db: Session):
    existing_admin = (
        db.query(Admin)
        .filter((Admin.Email == admin.Email) | (Admin.Username == admin.Username))
        .first()
    )

    if existing_admin:
        return error_response(
            message="Admin with this email or username already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    new_admin = Admin(
        Username=admin.Username,
        Email=admin.Email,
        Password=pwd_context.hash(admin.Password),
        RoleID=admin.RoleID,
    )

    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return success_response(
            message="Admin registered successfully",
            data=AdminResponseData.model_validate(new_admin).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message="Registration failed",
            details={"error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def login_admin(admin: AdminLogin, db: Session):
    admin_db = db.query(Admin).filter(Admin.Email == admin.Email).first()
    if not admin_db or not pwd_context.verify(admin.Password, admin_db.Password):
        return error_response(
            message="Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    admin_db.LastLogin = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": str(admin_db.AdminID), "role_id": admin_db.RoleID}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(admin_db.AdminID), "role_id": admin_db.RoleID}
    )
    return success_response(
        message="Login successful",
        data={
            "AdminID": admin_db.AdminID,
            "Username": admin_db.Username,
            "Role": admin_db.RoleID,
            "last_login": (
                admin_db.LastLogin.isoformat() if admin_db.LastLogin else None
            ),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    )


def get_all_admins(
    db: Session,
    current_admin_id: int,  # Use current_admin.AdminID
    page: int = 1,
    per_page: int = 10,
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    sort_by: Optional[AdminSortBy] = None,
    order: Optional[AdminOrder] = None,
):
    query = db.query(Admin)

    # Filtering
    if username:
        query = query.filter(Admin.Username.ilike(f"%{username}%"))
    if email:
        query = query.filter(Admin.Email.ilike(f"%{email}%"))
    if role:
        query = query.filter(Admin.Role == role)

    # Sorting
    sort_column = {
        AdminSortBy.admin_id: Admin.AdminID,
        AdminSortBy.username: Admin.Username,
        AdminSortBy.email: Admin.Email,
        AdminSortBy.role: Admin.RoleID,
        AdminSortBy.created_at: Admin.CreatedAt,
        AdminSortBy.last_login: Admin.LastLogin,
    }.get(
        sort_by, Admin.AdminID
    )  # Default to AdminID
    query = query.order_by(
        asc(sort_column) if order == AdminOrder.asc else desc(sort_column)
    )

    # Pagination
    total_admins = query.count()
    admins = query.offset((page - 1) * per_page).limit(per_page).all()
    admin_data = [
        AdminResponseData.model_validate(admin).model_dump() for admin in admins
    ]

    return PaginatedResponse(
        success=True,
        message="Admins retrieved successfully",
        data={"admins": admin_data},
        page=page,
        per_page=per_page,
        total_items=total_admins,
        total_pages=(total_admins + per_page - 1) // per_page,
    )


def toggle_user_active_status(user_id: int, current_admin_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()

    if not user:
        return error_response(
            message="User not found", status_code=status.HTTP_404_NOT_FOUND
        )

    user.IsActive = not user.IsActive
    if user.IsActive:  # If activating, set the approving admin
        user.ApprovedByAdminID = current_admin_id
    else:  # If deactivating, clear the approving admin
        user.ApprovedByAdminID = None

    db.commit()
    return success_response(
        message=f"User status updated successfully. New status: {'Active' if user.IsActive else 'Inactive'}",
        data={
            "UserID": user.UserID,
            "IsActive": user.IsActive,
            "ApprovedByAdminID": user.ApprovedByAdminID,
        },
    )


def get_all_users(
    page: int,
    per_page: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    isactive: Optional[bool] = None,
    account_type: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    sort_by: Optional[SortBy] = None,
    order: Optional[Order] = None,
    db: Session = None,
):
    query = db.query(User)

    # Apply filters
    if username:
        query = query.filter(User.Username.ilike(f"%{username}%"))
    if email:
        query = query.filter(User.Email.ilike(f"%{email}%"))
    if account_type:
        query = query.filter(User.AccountType == account_type)
    if balance_min is not None:
        query = query.filter(User.Balance >= balance_min)
    if balance_max is not None:
        query = query.filter(User.Balance <= balance_max)
    if isactive is not None:
        query = query.filter(User.IsActive == isactive)

    # Apply sorting
    sort_field = {
        SortBy.user_id: User.UserID,
        SortBy.username: User.Username,
        SortBy.email: User.Email,
        SortBy.balance: User.Balance,
        SortBy.created_at: User.CreatedAt,
        SortBy.last_login: User.LastLogin,
    }.get(
        sort_by, User.UserID
    )  # Default to UserID if sort_by is invalid

    sort_order = desc if order == Order.desc else asc
    query = query.order_by(sort_order(sort_field))

    # Pagination
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Users retrieved successfully",
        data={
            "users": [UserResponseData.model_validate(u).model_dump() for u in users]
        },
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    ).model_dump()


def update_user(user_id: int, user_update: UserUpdate, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Check for unique constraints
    if user_update.Username and user_update.Username != user.Username:
        if db.query(User).filter(User.Username == user_update.Username).first():
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Username already exists",
            )
    if user_update.Email and user_update.Email != user.Email:
        if db.query(User).filter(User.Email == user_update.Email).first():
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, message="Email already exists"
            )

    # Handle password update if provided
    update_data = user_update.model_dump(exclude_unset=True)
    if "Password" in update_data:
        user.Password = pwd_context.hash(
            update_data.pop("Password")
        )  # Hash and remove from update_data

    # Apply updates (including IsActive for admins)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
        return success_response(
            message="User updated successfully",
            data=UserResponseData.model_validate(user).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update user",
            details={"error": str(e)},
        )


def delete_user(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Check for active loans
    active_loans = (
        db.query(Loan)
        .filter(Loan.UserID == user_id, Loan.LoanStatus.in_(["Pending", "Approved"]))
        .count()
    )
    if active_loans > 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Cannot delete user with {active_loans} active loan(s)",
        )

    # Optionally check for non-zero balance or active transactions
    if user.Balance != 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot delete user with non-zero balance",
        )

    try:
        db.delete(user)
        db.commit()
        return success_response(
            message="User deleted successfully", data={"UserID": user_id}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete user",
            details={"error": str(e)},
        )
