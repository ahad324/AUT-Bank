# app/routes/users.py
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

# Controllers
from app.controllers.cards.users import (
    create_card,
    delete_card,
    list_cards,
    update_card,
)
from app.controllers.fetchtransactions.users import get_user_transactions
from app.controllers.transfers.users import create_transfer
from app.controllers.user_controller import (
    export_user_transactions,
    register_user,
    login_user,
    update_current_user,
    update_user_password,
    get_user_analytics_summary,
)
from app.controllers.loans.users import (
    apply_loan,
    get_loan_types,
    make_loan_payment,
    get_user_loans,
    get_loan_payments,
)

# Schemas
from app.schemas.card_schema import CardCreate, CardUpdate
from app.schemas.transfer_schema import TransferCreate
from app.schemas.user_schema import (
    PaginationParams,
    UserCreate,
    UserLogin,
    UserPasswordUpdate,
    UserUpdate,
)
from app.schemas.loan_schema import LoanApply, LoanPaymentCreate

# Models
from app.models.user import User

# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.auth import get_current_user, refresh_token
from app.core.rate_limiter import limiter, get_redis_client, CACHE_TTL
import json
import os

router = APIRouter()


@router.post("/register", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)


@router.post("/login", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "5/minute"))
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    return login_user(credentials, db)


@router.post("/refresh", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def refresh(request: Request, token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, User, "User", "UserID")


@router.get("/analytics/summary", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def get_user_analytics_summary_route(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_user_analytics_summary(current_user.UserID, db)


@router.get("/transactions", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_user_transactions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    params: PaginationParams = Depends(),
    transaction_type: Optional[str] = Query(None),
    transaction_status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sort_by: Optional[str] = Query("Timestamp"),
    order: Optional[str] = Query("desc"),
):
    # Generate a unique cache key based on user and query parameters
    cache_key = (
        f"transactions:user:{current_user.UserID}:page:{params.page}:per_page:{params.per_page}"
        f":type:{transaction_type or ''}:status:{transaction_status or ''}"
        f":start:{start_date or ''}:end:{end_date or ''}:sort:{sort_by}:order:{order}"
    )

    redis = get_redis_client()

    # Try to fetch from cache
    cached = redis.get(cache_key)
    if cached:
        return PaginatedResponse(**json.loads(cached))

    # Fetch from database if not cached
    result = get_user_transactions(
        user_id=current_user.UserID,
        db=db,
        page=params.page,
        per_page=params.per_page,
        transaction_type=transaction_type,
        transaction_status=transaction_status,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order,
    )

    # Cache the result
    redis.setex(cache_key, CACHE_TTL, json.dumps(result.model_dump()))
    return result


@router.post("/transfers", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def create_transfer_route(
    request: Request,
    transfer: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_transfer(current_user.UserID, transfer, db)


@router.get("/cards", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_cards_route(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_cards(current_user.UserID, db, page, per_page)


@router.post("/cards", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def create_card_route(
    request: Request,
    card: CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_card(current_user.UserID, card, db)


@router.put("/cards/{card_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def update_card_route(
    request: Request,
    card_id: int,
    card_update: CardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_card(current_user.UserID, card_id, card_update, db)


@router.delete("/cards/{card_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def delete_card_route(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return delete_card(current_user.UserID, card_id, db)


@router.post("/loans/apply", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def apply_for_loan(
    request: Request,
    loan: LoanApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return apply_loan(current_user.UserID, loan, db)


@router.get("/loans/types", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_loan_types(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_loan_types(db)


@router.post("/loans/payments", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def record_loan_payment(
    request: Request,
    payment: LoanPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return make_loan_payment(current_user.UserID, payment, db)


@router.get("/loans", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_user_loans(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("CreatedAt"),
    order: Optional[str] = Query("desc"),
):
    return get_user_loans(
        current_user.UserID, db, page, per_page, status, sort_by, order
    )


@router.get("/loans/{loan_id}/payments", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_loan_payments(
    request: Request,
    loan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    return get_loan_payments(current_user.UserID, loan_id, db, page, per_page)


@router.put("/me", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def update_current_user_route(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_current_user(current_user.UserID, user_update, db)


@router.put("/me/password", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def update_user_password_route(
    request: Request,
    password_update: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return update_user_password(current_user.UserID, password_update, db)


@router.get("/transactions/export")
@limiter.limit(os.getenv("RATE_LIMIT_EXPORT", "5/hour"))
def export_user_transactions_route(
    request: Request,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    transaction_status: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return export_user_transactions(
        current_user.UserID,
        db,
        start_date,
        end_date,
        transaction_status,
        transaction_type,
    )
