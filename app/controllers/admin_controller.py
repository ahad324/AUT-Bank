from fastapi import status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone
# Schemas
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminResponseData
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
    
    admin_db.LastLogin = datetime.now(timezone.utc).replace(tzinfo=None)
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