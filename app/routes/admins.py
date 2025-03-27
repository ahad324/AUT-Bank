from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.controllers.admin_controller import register_admin, login_admin
from app.controllers.transaction_controller import get_all_transactions
from app.schemas.admin_schema import AdminCreate, AdminLogin
from app.core.database import get_db
from app.core.schemas import BaseResponse
from app.core.auth import get_current_admin
from app.models.admin import Admin

router = APIRouter(tags=["Admin Management"])

@router.post("/register", response_model=BaseResponse)
def register(admin: AdminCreate, db: Session = Depends(get_db)):
    return register_admin(admin, db)

@router.post("/login", response_model=BaseResponse)
def login(admin: AdminLogin, db: Session = Depends(get_db)):
    return login_admin(admin, db)

@router.get("/transactions", response_model=BaseResponse)
def list_transactions(
    page: int = 1,
    per_page: int = 10,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return get_all_transactions(page, per_page, db)