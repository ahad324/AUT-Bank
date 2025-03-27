from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
#  Controllers
from app.controllers.admin_controller import register_admin, login_admin
from app.controllers.transaction_controller import get_all_transactions, get_user_transactions_for_admin, get_transaction_by_id
from app.controllers.user_controller import get_all_users, get_user_by_id
from app.controllers.loan_controller import approve_loan, get_all_loans, get_user_loans_for_admin, get_loan_by_id
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

@router.get("/transactions", response_model=dict)
def list_all_transactions(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sender_id: Optional[int] = Query(None, description="Filter by sender ID"),
    receiver_id: Optional[int] = Query(None, description="Filter by receiver ID"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("Timestamp", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_all_transactions(
        db=db,
        page=page,
        per_page=per_page,
        transaction_type=transaction_type,
        status=status,
        sender_id=sender_id,
        receiver_id=receiver_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )

@router.get("/users/{user_id}/transactions", response_model=dict)
def list_user_transactions_for_admin(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("Timestamp", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_user_transactions_for_admin(
        user_id=user_id,
        db=db,
        page=page,
        per_page=per_page,
        transaction_type=transaction_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )

@router.get("/transactions/{transaction_id}", response_model=BaseResponse)
def get_single_transaction(
    transaction_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return get_transaction_by_id(transaction_id, db)

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

@router.post("/loans/{loan_id}/approve", response_model=BaseResponse)
def approve_or_reject_loan(
    loan_id: int,
    new_status: str = Query(..., description="Status: Approved or Rejected"),
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return approve_loan(loan_id, new_status, current_admin, db)

@router.get("/loans", response_model=dict)
def list_all_loans(
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    loan_status: Optional[str] = Query(None, description="Filter by loan status"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    loan_type_id: Optional[int] = Query(None, description="Filter by loan type ID"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("CreatedAt", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_all_loans(
        db=db,
        page=page,
        per_page=per_page,
        loan_status=loan_status,
        user_id=user_id,
        loan_type_id=loan_type_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )

@router.get("/users/{user_id}/loans", response_model=dict)
def list_user_loans_for_admin(
    user_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    loan_status: Optional[str] = Query(None, description="Filter by loan status"),
    loan_type_id: Optional[int] = Query(None, description="Filter by loan type ID"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("CreatedAt", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_user_loans_for_admin(
        user_id=user_id,
        db=db,
        page=page,
        per_page=per_page,
        loan_status=loan_status,
        loan_type_id=loan_type_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order
    )

@router.get("/loans/{loan_id}", response_model=BaseResponse)
def get_single_loan(
    loan_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    return get_loan_by_id(loan_id, db)