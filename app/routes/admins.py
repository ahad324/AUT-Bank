# app/routes/admins.py
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from app.core.rate_limiter import limiter, get_redis_client, CACHE_TTL
import json

# Controllers
from app.controllers.admin_controller import (
    delete_user,
    export_transactions,
    get_all_admins,
    register_admin,
    login_admin,
    toggle_user_active_status,
    update_user,
    get_analytics_summary,
)
from app.controllers.deposits.admins import create_deposit
from app.controllers.admin_controller import get_all_users
from app.controllers.fetchtransactions.admins import get_all_transactions
from app.controllers.loans.admins import approve_loan, get_all_loans
from app.controllers.cards.admins import list_all_cards, block_card, update_card_admin

# Schemas
from app.core.exceptions import CustomHTTPException
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminOrder, AdminSortBy
from app.schemas.card_schema import CardUpdate
from app.schemas.deposit_schema import DepositCreate
from app.schemas.user_schema import Order, SortBy, UserUpdate

# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.auth import refresh_token
from app.core.rbac import check_permission

# Models
from app.models.admin import Admin
import os

router = APIRouter()


@router.post("/bootstrap-admin", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def bootstrap_admin(
    request: Request, admin: AdminCreate, db: Session = Depends(get_db)
):
    if db.query(Admin).count() > 0:
        raise CustomHTTPException(
            status_code=403, message="Admin bootstrap only allowed when no admins exist"
        )
    return register_admin(admin, db)


@router.post("/register", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def register(
    request: Request,
    admin: AdminCreate,
    current_admin: Admin = Depends(check_permission("admin:register")),
    db: Session = Depends(get_db),
):
    return register_admin(admin, db)


@router.post("/login", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "5/minute"))
def login(request: Request, credentials: AdminLogin, db: Session = Depends(get_db)):
    return login_admin(credentials, db)


@router.post("/refresh", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def refresh(request: Request, token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, Admin, "Admin", "AdminID")


@router.get("/analytics/summary", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def get_analytics_summary_route(
    request: Request,
    current_admin: Admin = Depends(check_permission("analytics:view")),
    db: Session = Depends(get_db),
):
    # Cache key based on endpoint and admin ID (since it's admin-specific)
    cache_key = f"analytics:summary:admin:{current_admin.AdminID}"

    redis = get_redis_client()

    # Try to fetch from cache
    cached = redis.get(cache_key)
    if cached:
        return BaseResponse(**json.loads(cached))

    # Fetch from database if not cached
    result = get_analytics_summary(db)

    # Cache the result
    redis.setex(cache_key, CACHE_TTL, json.dumps(result))
    return result


@router.get("/admins", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_all_admins(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    username: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    sort_by: Optional[AdminSortBy] = Query(None),
    order: Optional[AdminOrder] = Query(None),
    current_admin: Admin = Depends(check_permission("admin:view_all")),
    db: Session = Depends(get_db),
):
    return get_all_admins(
        db,
        current_admin_id=current_admin.AdminID,
        page=page,
        per_page=per_page,
        username=username,
        email=email,
        role=role,
        sort_by=sort_by,
        order=order,
    )


@router.put("/users/toggle-user-status/{user_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def toggle_user_status(
    request: Request,
    user_id: int,
    current_admin: Admin = Depends(check_permission("user:approve")),
    db: Session = Depends(get_db),
):
    return toggle_user_active_status(user_id, current_admin.AdminID, db)


@router.get("/users", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_users(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    username: Optional[str] = None,
    email: Optional[str] = None,
    isactive: Optional[bool] = None,
    account_type: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    sort_by: Optional[SortBy] = None,
    order: Optional[Order] = None,
    current_admin: Admin = Depends(check_permission("user:view_all")),
    db: Session = Depends(get_db),
):
    return get_all_users(
        page,
        per_page,
        username,
        email,
        isactive,
        account_type,
        balance_min,
        balance_max,
        sort_by,
        order,
        db,
    )


@router.post("/users/{user_id}/deposits", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def create_deposit_route(
    request: Request,
    user_id: int,
    deposit: DepositCreate,
    current_admin: Admin = Depends(check_permission("deposit:manage")),
    db: Session = Depends(get_db),
):
    return create_deposit(user_id, current_admin.AdminID, deposit, db)


@router.get("/loans", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_all_loans(
    request: Request,
    current_admin: Admin = Depends(check_permission("loan:view_all")),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    loan_status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    loan_type_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sort_by: Optional[str] = Query("CreatedAt"),
    order: Optional[str] = Query("desc"),
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
        order=order,
    )


@router.post("/loans/{loan_id}/approve", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def approve_or_reject_loan(
    request: Request,
    loan_id: int,
    new_status: str = Query(...),
    current_admin: Admin = Depends(check_permission("loan:approve")),
    db: Session = Depends(get_db),
):
    return approve_loan(loan_id, new_status, current_admin, db)


@router.put("/users/{user_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def update_user_route(
    request: Request,
    user_id: int,
    user_update: UserUpdate,
    current_admin: Admin = Depends(check_permission("user:update")),
    db: Session = Depends(get_db),
):
    return update_user(user_id, user_update, db)


@router.delete("/users/{user_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def delete_user_route(
    request: Request,
    user_id: int,
    current_admin: Admin = Depends(check_permission("user:delete")),
    db: Session = Depends(get_db),
):
    return delete_user(user_id, db)


@router.get("/transactions", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_all_transactions(
    request: Request,
    current_admin: Admin = Depends(check_permission("transaction:view_all")),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    transaction_type: Optional[str] = Query(None),
    transaction_status: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    sort_by: Optional[str] = Query("Timestamp"),
    order: Optional[str] = Query("desc"),
):
    return get_all_transactions(
        db=db,
        page=page,
        per_page=per_page,
        transaction_type=transaction_type,
        transaction_status=transaction_status,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        order=order,
    )


@router.get("/cards", response_model=PaginatedResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def list_all_cards_route(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    user_id: Optional[int] = Query(None),
    current_admin: Admin = Depends(check_permission("card:view_all")),
    db: Session = Depends(get_db),
):
    return list_all_cards(db, page, per_page, user_id)


@router.put("/cards/{card_id}/block", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def block_card_route(
    request: Request,
    card_id: int,
    current_admin: Admin = Depends(check_permission("card:manage")),
    db: Session = Depends(get_db),
):
    return block_card(card_id, db)


@router.put("/cards/{card_id}", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_ADMIN_CRITICAL", "10/minute"))
def update_card_admin_route(
    request: Request,
    card_id: int,
    card_update: CardUpdate,
    current_admin: Admin = Depends(check_permission("card:manage")),
    db: Session = Depends(get_db),
):
    return update_card_admin(card_id, card_update, db)


@router.get("/transactions/export")
@limiter.limit(os.getenv("RATE_LIMIT_EXPORT", "5/hour"))
def export_transactions_route(
    request: Request,
    user_id: Optional[int] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    transaction_status: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    current_admin: Admin = Depends(check_permission("transactions:export")),
    db: Session = Depends(get_db),
):
    return export_transactions(
        db, user_id, start_date, end_date, transaction_status, transaction_type
    )
