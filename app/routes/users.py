# app/routes/users.py
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, BackgroundTasks
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
from app.core.rate_limiter import (
    limiter,
    get_redis_client,
    CACHE_TTL_SHORT,
    CACHE_TTL_MEDIUM,
    CACHE_TTL_LONG,
    get_cache_key,
    get_from_cache,
    set_to_cache,
    invalidate_cache,
)
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
    cache_key = get_cache_key(request, "user_analytics:summary", current_user.UserID)
    cached = get_from_cache(cache_key)
    if cached:
        return BaseResponse(**cached)
    result = get_user_analytics_summary(current_user.UserID, db)
    set_to_cache(cache_key, result, CACHE_TTL_SHORT)  # 5 min TTL
    return result


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
    query_params = {
        "page": params.page,
        "per_page": params.per_page,
        "transaction_type": transaction_type,
        "transaction_status": transaction_status,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "sort_by": sort_by,
        "order": order,
    }
    cache_key = get_cache_key(
        request, "user_transactions", current_user.UserID, query_params
    )
    cached = get_from_cache(cache_key)
    if cached:
        return PaginatedResponse(**cached)
    result = get_user_transactions(
        current_user.UserID,
        db,
        params.page,
        params.per_page,
        transaction_type,
        transaction_status,
        start_date,
        end_date,
        sort_by,
        order,
    )
    set_to_cache(cache_key, result.model_dump(), CACHE_TTL_SHORT)  # 5 min TTL
    return result


@router.post("/transfers", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
async def create_transfer_route(
    request: Request,
    transfer: TransferCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = await create_transfer(current_user.UserID, transfer, db, background_tasks)
    invalidate_cache(f"user_analytics:summary:user:{current_user.UserID}")
    invalidate_cache(f"user_transactions:user:{current_user.UserID}")
    return result


@router.get("/cards", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_cards_route(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    params = {"page": page, "per_page": per_page}
    cache_key = get_cache_key(request, "user_cards", current_user.UserID, params)
    cached = get_from_cache(cache_key)
    if cached:
        return PaginatedResponse(**cached)
    result = list_cards(current_user.UserID, db, page, per_page)
    set_to_cache(cache_key, result.model_dump(), CACHE_TTL_MEDIUM)  # 1 hr TTL
    return result


@router.post("/cards", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def create_card_route(
    request: Request,
    card: CardCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = create_card(current_user.UserID, card, db)
    invalidate_cache(f"user_cards:user:{current_user.UserID}")
    return result


@router.put("/cards/{card_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def update_card_route(
    request: Request,
    card_id: int,
    card_update: CardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_card(current_user.UserID, card_id, card_update, db)
    invalidate_cache(f"user_cards:user:{current_user.UserID}")
    return result


@router.delete("/cards/{card_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def delete_card_route(
    request: Request,
    card_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = delete_card(current_user.UserID, card_id, db)
    invalidate_cache(f"user_cards:user:{current_user.UserID}")
    return result


@router.post("/loans/apply", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def apply_for_loan(
    request: Request,
    loan: LoanApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = apply_loan(current_user.UserID, loan, db)
    invalidate_cache(f"user_loans:user:{current_user.UserID}")
    invalidate_cache(f"user_analytics:summary:user:{current_user.UserID}")
    return result


@router.get("/loans/types", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_loan_types(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cache_key = get_cache_key(request, "loan_types")
    cached = get_from_cache(cache_key)
    if cached:
        return BaseResponse(**cached)
    result = get_loan_types(db)
    set_to_cache(cache_key, result, CACHE_TTL_LONG)  # 24 hr TTL for static data
    return result


@router.post("/loans/payments", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def record_loan_payment(
    request: Request,
    payment: LoanPaymentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = make_loan_payment(current_user.UserID, payment, db)
    invalidate_cache(f"user_loans:user:{current_user.UserID}")
    invalidate_cache(f"user_analytics:summary:user:{current_user.UserID}")
    return result


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
    params = {
        "page": page,
        "per_page": per_page,
        "status": status,
        "sort_by": sort_by,
        "order": order,
    }
    cache_key = get_cache_key(request, "user_loans", current_user.UserID, params)
    cached = get_from_cache(cache_key)
    if cached:
        return PaginatedResponse(**cached)
    result = get_user_loans(
        current_user.UserID, db, page, per_page, status, sort_by, order
    )
    set_to_cache(cache_key, result.model_dump(), CACHE_TTL_MEDIUM)  # 1 hr TTL
    return result


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
    params = {"page": page, "per_page": per_page}
    cache_key = get_cache_key(
        request, f"user_loan_payments:{loan_id}", current_user.UserID, params
    )
    cached = get_from_cache(cache_key)
    if cached:
        return PaginatedResponse(**cached)
    result = get_loan_payments(current_user.UserID, loan_id, db, page, per_page)
    set_to_cache(cache_key, result.model_dump(), CACHE_TTL_MEDIUM)  # 1 hr TTL
    return result


@router.put("/me", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def update_current_user_route(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = update_current_user(current_user.UserID, user_update, db)
    invalidate_cache(f"user_analytics:summary:user:{current_user.UserID}")
    return result


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
