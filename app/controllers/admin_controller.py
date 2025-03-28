from typing import Optional
from fastapi import status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone
# Schemas
from app.core.exceptions import CustomHTTPException
from app.core.schemas import PaginatedResponse
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminOrder, AdminResponseData, AdminSortBy
# Models
from app.models.admin import Admin
# Core
from app.core.auth import create_access_token, create_refresh_token
from app.core.responses import success_response, error_response

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
       