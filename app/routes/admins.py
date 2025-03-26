from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.controllers.admin_controller import register_admin, login_admin
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminResponse
from app.core.database import get_db

router = APIRouter()

@router.post("/register", response_model=AdminResponse)
def register(admin: AdminCreate, db: Session = Depends(get_db)):
    return register_admin(admin, db)

@router.post("/login", response_model=AdminResponse)
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    return login_admin(admin, db)