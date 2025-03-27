from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
#  Controllers
from app.controllers.admin_controller import register_admin, login_admin
from app.controllers.transaction_controller import get_all_transactions
from app.controllers.user_controller import get_all_users, get_user_by_id
# Schemas
from app.schemas.admin_schema import AdminCreate, AdminLogin
from app.schemas.user_schema import Order, SortBy
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse
from app.core.auth import get_current_admin, refresh_token
# Models
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

@router.get("/users", response_model=BaseResponse)
def list_users(
    page: int = 1,
    per_page: int = 10,
    username: Optional[str] = None,
    email: Optional[str] = None,
    account_type: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    sort_by: Optional[SortBy] = None,
    order: Optional[Order] = None,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return get_all_users(page, per_page, username, email, account_type, balance_min, balance_max, sort_by, order, db)

@router.get("/users/{user_id}", response_model=BaseResponse)
def get_user(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return get_user_by_id(user_id, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, Admin, "Admin", "AdminID")