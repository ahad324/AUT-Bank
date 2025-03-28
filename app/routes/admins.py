from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
#  Controllers
from app.controllers.admin_controller import get_admin_by_id, get_all_admins, register_admin, login_admin
from app.controllers.transactions.admins import get_all_transactions, get_user_transactions_for_admin, get_transaction_by_id
from app.controllers.user_controller import get_all_users, get_user_by_id
from app.controllers.loans.admins import approve_loan, get_all_loans, get_user_loans_for_admin, get_loan_by_id
# Schemas
from app.core.exceptions import CustomHTTPException
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminOrder, AdminSortBy
from app.schemas.user_schema import Order, SortBy
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.auth import refresh_token
from app.core.rbac import PERMISSION_VIEW_ADMIN_DETAILS, PERMISSION_VIEW_ALL_ADMINS, require_permission, PERMISSION_REGISTER_ADMIN, PERMISSION_APPROVE_LOAN, \
    PERMISSION_VIEW_ALL_LOANS, PERMISSION_VIEW_USER_LOANS, PERMISSION_VIEW_LOAN_DETAILS, \
    PERMISSION_VIEW_ALL_TRANSACTIONS, PERMISSION_VIEW_USER_TRANSACTIONS, PERMISSION_VIEW_TRANSACTION_DETAILS, \
    PERMISSION_VIEW_ALL_USERS, PERMISSION_VIEW_USER_DETAILS
# Models
from app.models.admin import Admin

router = APIRouter(tags=["Admin Management"])


# <============ Temporary Route ============>
@router.post("/bootstrap-admin", response_model=BaseResponse)
def bootstrap_admin(
    admin: AdminCreate,
    db: Session = Depends(get_db)
):
    # Check if any admins exist
    if db.query(Admin).count() > 0:
        raise CustomHTTPException(status_code=403, message="Admin bootstrap only allowed when no admins exist")
    return register_admin(admin, db)
@router.post("/register", response_model=BaseResponse)

# <==========================================>



def register(
    admin: AdminCreate,
    current_admin: Admin = Depends(require_permission(PERMISSION_REGISTER_ADMIN)),
    db: Session = Depends(get_db)
):
    return register_admin(admin, db)

@router.post("/login", response_model=BaseResponse)
def login(
    credentials: AdminLogin,
    db: Session = Depends(get_db)
):
    return login_admin(credentials, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, Admin, "Admin", "AdminID")

@router.get("/admins", response_model=PaginatedResponse)
def list_all_admins(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    username: Optional[str] = Query(None, description="Filter by username"),
    email: Optional[str] = Query(None, description="Filter by email"),
    role: Optional[str] = Query(None, description="Filter by role (SuperAdmin, Manager, Auditor)"),
    sort_by: Optional[AdminSortBy] = Query(None, description="Sort by field"),
    order: Optional[AdminOrder] = Query(None, description="Sort order: asc or desc"),
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ALL_ADMINS)),
    db: Session = Depends(get_db)
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
        order=order
    )

@router.get("/admins/{admin_id}", response_model=BaseResponse)
def get_single_admin(
    admin_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ADMIN_DETAILS)),
    db: Session = Depends(get_db)
):
    return get_admin_by_id(admin_id, current_admin.AdminID, db)

@router.get("/users", response_model=PaginatedResponse)
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
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ALL_USERS)),
    db: Session = Depends(get_db)
):
    return get_all_users(page, per_page, username, email, account_type, balance_min, balance_max, sort_by, order, db)

@router.get("/users/{user_id}", response_model=BaseResponse)
def get_user(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_USER_DETAILS)),
    db: Session = Depends(get_db)
):
    return get_user_by_id(user_id, db)

@router.get("/transactions", response_model= PaginatedResponse)
def list_all_transactions(
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ALL_TRANSACTIONS)),
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

@router.get("/transactions/{transaction_id}", response_model=BaseResponse)
def get_single_transaction(
    transaction_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_TRANSACTION_DETAILS)),
    db: Session = Depends(get_db)
):
    return get_transaction_by_id(transaction_id, db)

@router.get("/users/{user_id}/transactions", response_model=PaginatedResponse)
def list_user_transactions_for_admin(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_USER_TRANSACTIONS)),
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

@router.get("/loans", response_model=PaginatedResponse)
def list_all_loans(
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ALL_LOANS)),
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
    
@router.post("/loans/{loan_id}/approve", response_model=BaseResponse)
def approve_or_reject_loan(
    loan_id: int,
    new_status: str = Query(..., description="Status: Approved or Rejected"),
    current_admin: Admin = Depends(require_permission(PERMISSION_APPROVE_LOAN)),
    db: Session = Depends(get_db)
):
    return approve_loan(loan_id, new_status, current_admin, db)

@router.get("/users/{user_id}/loans", response_model=PaginatedResponse)
def list_user_loans_for_admin(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_USER_LOANS)),
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
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_LOAN_DETAILS)),
    db: Session = Depends(get_db)
):
    return get_loan_by_id(loan_id, db)