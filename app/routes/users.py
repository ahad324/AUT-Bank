from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
# Controllers
from app.controllers.user_controller import register_user, login_user
from app.controllers.transactions.users import create_transaction, get_user_transaction_by_id, get_user_transactions
from app.controllers.loans.users import apply_loan, get_loan_types, get_user_loan_by_id, make_loan_payment, get_user_loans, get_loan_payments
# Schemas
from app.schemas.user_schema import PaginationParams, UserCreate, UserLogin
from app.schemas.transaction_schema import TransactionCreate
from app.schemas.loan_schema import LoanApply, LoanPaymentCreate
# Models
from app.models.user import User
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.auth import get_current_user, refresh_token

router = APIRouter()

@router.post("/register", response_model=BaseResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login", response_model=BaseResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    return login_user(credentials, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, User, "User", "UserID")

@router.post("/transactions", response_model=BaseResponse)
def perform_transaction(
    transaction: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_transaction(current_user.UserID, transaction, db)

@router.get("/transactions", response_model=PaginatedResponse)
def list_user_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    params: PaginationParams = Depends(),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[date] = Query(None, description="Filter by start date"),
    end_date: Optional[date] = Query(None, description="Filter by end date"),
    sort_by: Optional[str] = Query("Timestamp", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
):
    return get_user_transactions(
        user_id=current_user.UserID,
        db=db,
        page=params.page,
        per_page=params.per_page,
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_user_transaction_by_id(current_user.UserID, transaction_id, db)

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

@router.get("/loans", response_model=PaginatedResponse)
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

@router.get("/loans/{loan_id}", response_model=BaseResponse)
def get_single_loan(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_user_loan_by_id(current_user.UserID, loan_id, db)

@router.get("/loans/{loan_id}/payments", response_model=PaginatedResponse)
def list_loan_payments(
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100)
):
    return get_loan_payments(current_user.UserID, loan_id, db, page, per_page)