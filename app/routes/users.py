from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
# Controller
from app.controllers.user_controller import register_user, login_user
from app.controllers.transaction_controller import create_transaction
from app.controllers.loan_controller import apply_loan, get_loan_types, make_loan_payment, get_user_loans, get_loan_payments
# Schemas
from app.schemas.user_schema import UserCreate, UserLogin
from app.schemas.transaction_schema import TransactionCreate
from app.schemas.loan_schema import LoanApply, LoanPaymentCreate
# Models
from app.models.user import User
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse
from app.core.auth import get_current_user, refresh_token

router = APIRouter()

@router.post("/register", response_model=BaseResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login", response_model=BaseResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    return login_user(credentials, db)

@router.post("/transactions", response_model=BaseResponse)
def perform_transaction(
    transaction: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_transaction(current_user.UserID, transaction, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, User, "User", "UserID")

@router.post("/loans/apply", response_model=BaseResponse)
def apply_for_loan(
    loan: LoanApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return apply_loan(current_user.UserID, loan, db)

@router.get("/loans/types", response_model=BaseResponse)
def list_loan_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_loan_types(db)

@router.post("/loans/payments", response_model=BaseResponse)
def record_loan_payment(
    payment: LoanPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return make_loan_payment(current_user.UserID, payment, db)

@router.get("/loans", response_model=BaseResponse)
def list_user_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by loan status"),
    sort_by: Optional[str] = Query("CreatedAt", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_user_loans(current_user.UserID, db, page, per_page, status, sort_by, order)

@router.get("/loans/{loan_id}/payments", response_model=BaseResponse)
def list_loan_payments(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    return get_loan_payments(current_user.UserID, loan_id, db, page, per_page)