from typing import Optional
from fastapi import status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone
# Schemas
from app.core.exceptions import CustomHTTPException
from app.core.schemas import PaginatedResponse
from app.models.user import User
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminOrder, AdminResponseData, AdminSortBy
# Models
from app.models.admin import Admin
# Core
from app.core.auth import create_access_token, create_refresh_token
from app.core.responses import success_response, error_response
from app.schemas.user_schema import Order, SortBy, UserResponseData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def register_admin(admin: AdminCreate, db: Session):
    existing_admin = db.query(Admin).filter(
        (Admin.Email == admin.Email) | 
        (Admin.Username == admin.Username)
    ).first()
    
    if existing_admin:
        return error_response(
            message="Admin with this email or username already exists",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    new_admin = Admin(
        Username=admin.Username,
        Email=admin.Email,
        PasswordHash=pwd_context.hash(admin.Password),
        Role=admin.Role.value
    )
    
    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return success_response(
            message="Admin registered successfully",
            data=AdminResponseData.model_validate(new_admin).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message="Registration failed",
            details={"error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def login_admin(admin: AdminLogin, db: Session):
    admin_db = db.query(Admin).filter(Admin.Email == admin.Email).first()
    if not admin_db or not pwd_context.verify(admin.Password, admin_db.PasswordHash):
        return error_response(
            message="Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    admin_db.LastLogin = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": str(admin_db.AdminID), "role": "Admin"})
    refresh_token = create_refresh_token(data={"sub": str(admin_db.AdminID), "role": "Admin"})
    return success_response(
        message="Login successful",
        data={
            "AdminID": admin_db.AdminID,
            "Username": admin_db.Username,
            "Role": admin_db.Role,
            "last_login": admin_db.LastLogin.isoformat() if admin_db.LastLogin else None,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
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
    order: Optional[AdminOrder] = None
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
        AdminSortBy.role: Admin.Role,
        AdminSortBy.created_at: Admin.CreatedAt,
        AdminSortBy.last_login: Admin.LastLogin
    }.get(sort_by, Admin.AdminID)  # Default to AdminID
    query = query.order_by(asc(sort_column) if order == AdminOrder.asc else desc(sort_column))
    
    # Pagination
    total_admins = query.count()
    admins = query.offset((page - 1) * per_page).limit(per_page).all()
    admin_data = [AdminResponseData.model_validate(admin).model_dump() for admin in admins]
    
    return PaginatedResponse(
        success=True,
        message="Admins retrieved successfully",
        data={"admins": admin_data},
        page=page,
        per_page=per_page,
        total_items=total_admins,
        total_pages=(total_admins + per_page - 1) // per_page
    )

def get_admin_by_id(admin_id: int, current_admin_id: int, db: Session):
    admin = db.query(Admin).filter(Admin.AdminID == admin_id).first()
    if not admin:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Admin not found",
            details={}
        )
    # Optional: Restrict visibility (e.g., Auditor can't see SuperAdmin)
    # if current_admin.Role == "Auditor" and admin.Role in ["SuperAdmin", "Manager"]:
    #     raise CustomHTTPException(status_code=403, message="Permission denied")
    
    return success_response(
        message="Admin retrieved successfully",
        data=AdminResponseData.model_validate(admin).model_dump()
    )

def toggle_user_active_status(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()

    if not user:
        return error_response(
            message="User not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    user.IsActive = not user.IsActive  # Toggle the status
    db.commit()
    return success_response(
        message=f"User status updated successfully. New status: {'Active' if user.IsActive else 'Inactive'}",
        data={"UserID": user.UserID, "IsActive": user.IsActive}
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
    db: Session = None
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
        SortBy.last_login: User.LastLogin
    }.get(sort_by, User.UserID)  # Default to UserID if sort_by is invalid

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
        data={"users": [UserResponseData.model_validate(u).model_dump() for u in users]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()
    
def get_user_by_id(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            details={}
        )
    return success_response(
        message="User retrieved successfully",
        data=UserResponseData.model_validate(user).model_dump()
    )
           