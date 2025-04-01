from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
#  Controllers
from app.controllers.admin_controller import delete_user, get_admin_by_id, get_all_admins, register_admin, login_admin, toggle_user_active_status, update_user
from app.controllers.deposits.admins import create_deposit
from app.controllers.admin_controller import get_all_users, get_user_by_id
from app.controllers.loans.admins import approve_loan, get_all_loans, get_user_loans_for_admin, get_loan_by_id
# Schemas
from app.core.exceptions import CustomHTTPException
from app.schemas.admin_schema import AdminCreate, AdminLogin, AdminOrder, AdminSortBy
from app.schemas.deposit_schema import DepositCreate
from app.schemas.user_schema import Order, SortBy, UserUpdate
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.auth import refresh_token
from app.core.rbac import PERMISSION_APPROVE_USER, PERMISSION_DELETE_USER, PERMISSION_MANAGE_DEPOSITS, PERMISSION_UPDATE_USER, PERMISSION_VIEW_ADMIN_DETAILS, PERMISSION_VIEW_ALL_ADMINS, require_permission, PERMISSION_REGISTER_ADMIN, PERMISSION_APPROVE_LOAN, \
    PERMISSION_VIEW_ALL_LOANS, PERMISSION_VIEW_USER_LOANS, PERMISSION_VIEW_LOAN_DETAILS, \
    PERMISSION_VIEW_ALL_USERS, PERMISSION_VIEW_USER_DETAILS
# Models
from app.models.admin import Admin

router = APIRouter()


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

# <==========================================>



@router.post("/register", response_model=BaseResponse)
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

@router.put("/users/toggle-user-status/{user_id}", response_model=BaseResponse)
def toggle_user_status(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_APPROVE_USER)),
    db: Session = Depends(get_db)
):
    return toggle_user_active_status(user_id, db) 

@router.get("/users", response_model=PaginatedResponse)
def list_users(
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
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_ALL_USERS)),
    db: Session = Depends(get_db)
):
    return get_all_users(page, per_page, username, email, isactive, account_type, balance_min, balance_max, sort_by, order, db)

@router.get("/users/{user_id}", response_model=BaseResponse)
def get_user(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_VIEW_USER_DETAILS)),
    db: Session = Depends(get_db)
):
    return get_user_by_id(user_id, db)

@router.post("/users/{user_id}/deposits", response_model=BaseResponse)
def create_deposit_route(
    user_id: int,
    deposit: DepositCreate,
    current_admin: Admin = Depends(require_permission(PERMISSION_MANAGE_DEPOSITS)),
    db: Session = Depends(get_db)
):
    return create_deposit(user_id, current_admin.AdminID, deposit, db)

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


@router.put("/users/{user_id}", response_model=BaseResponse)
def update_user_route(
    user_id: int,
    user_update: UserUpdate,
    current_admin: Admin = Depends(require_permission(PERMISSION_UPDATE_USER)),
    db: Session = Depends(get_db)
):
    return update_user(user_id, user_update, db)

@router.delete("/users/{user_id}", response_model=BaseResponse)
def delete_user_route(
    user_id: int,
    current_admin: Admin = Depends(require_permission(PERMISSION_DELETE_USER)),
    db: Session = Depends(get_db)
):
    return delete_user(user_id, db)