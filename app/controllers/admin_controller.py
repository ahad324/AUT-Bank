from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminResponse
from app.models.admin import Admin
from app.core.database import get_db
from datetime import datetime, timezone

router = APIRouter(tags=["Admin Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
def register_admin(admin: AdminCreate, db: Session = Depends(get_db)):
    # Check if admin already exists
    existing_admin = db.query(Admin).filter(
        (Admin.Email == admin.Email) | 
        (Admin.Username == admin.Username)
    ).first()
    
    if existing_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email or username already exists"
        )

    # Create new admin
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
        return new_admin
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login")
def login_admin(admin: AdminLogin, db: Session = Depends(get_db)):
    # Find admin by email
    admin_db = db.query(Admin).filter(Admin.Email == admin.Email).first()
    if not admin_db or not pwd_context.verify(admin.Password, admin_db.PasswordHash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    admin_db.LastLogin = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    return {
        "message": "Login successful",
        "admin_id": admin_db.AdminID,
        "username": admin_db.Username,
        "role": admin_db.Role,
        "last_login": admin_db.LastLogin.isoformat() if admin_db.LastLogin else None
    }