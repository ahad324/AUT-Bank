from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
# Controllers
from app.controllers.cards.users import create_card
from app.controllers.transfers.users import create_transfer
from app.controllers.user_controller import register_user, login_user, update_current_user, update_user_password

from app.controllers.loans.users import apply_loan, get_loan_types, get_user_loan_by_id, make_loan_payment, get_user_loans, get_loan_payments
# Schemas
from app.schemas.card_schema import CardCreate
from app.schemas.transfer_schema import TransferCreate
from app.schemas.user_schema import PaginationParams, UserCreate, UserLogin, UserPasswordUpdate, UserUpdate
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

@router.post("/transfers", response_model=BaseResponse)
def create_transfer_route(
    transfer: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_transfer(current_user.UserID, transfer, db)

@router.post("/cards", response_model=BaseResponse)
def create_card_route(
    card: CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_card(current_user.UserID, card, db)

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


@router.put("/me", response_model=BaseResponse)
def update_current_user_route(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_current_user(current_user.UserID, user_update, db)

@router.put("/me/password", response_model=BaseResponse)
def update_user_password_route(
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return update_user_password(current_user.UserID, password_update, db)