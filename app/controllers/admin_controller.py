from io import StringIO
import csv
from fastapi.responses import StreamingResponse
from typing import Optional
from fastapi import status
from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone

# Schemas
from app.core.exceptions import CustomHTTPException
from app.core.schemas import PaginatedResponse
from app.models.loan import Loan
from app.models.user import User
from app.schemas.admin_schema import (
    AdminCreate,
    AdminLogin,
    AdminOrder,
    AdminResponseData,
    AdminSortBy,
)

# Models
from app.models.admin import Admin
from app.models.deposit import Deposit
from app.models.transfer import Transfer
from app.models.withdrawal import Withdrawal

# Core
from app.core.auth import create_access_token, create_refresh_token
from app.core.responses import success_response, error_response
from app.schemas.user_schema import Order, SortBy, UserResponseData, UserUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_admin(admin: AdminCreate, db: Session):
    existing_admin = (
        db.query(Admin)
        .filter((Admin.Email == admin.Email) | (Admin.Username == admin.Username))
        .first()
    )

    if existing_admin:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Admin with this email or username already exists",
        )

    new_admin = Admin(
        Username=admin.Username,
        Email=admin.Email,
        Password=pwd_context.hash(admin.Password),
        RoleID=admin.RoleID,
    )

    try:
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        return success_response(
            message="Admin registered successfully",
            data=AdminResponseData.model_validate(new_admin).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message="Registration failed",
            details={"error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def login_admin(admin: AdminLogin, db: Session):
    admin_db = db.query(Admin).filter(Admin.Email == admin.Email).first()
    if not admin_db or not pwd_context.verify(admin.Password, admin_db.Password):
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message="Invalid email or password",
        )

    admin_db.LastLogin = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": str(admin_db.AdminID), "role_id": admin_db.RoleID}
    )
    refresh_token = create_refresh_token(
        data={"sub": str(admin_db.AdminID), "role_id": admin_db.RoleID}
    )
    return success_response(
        message="Login successful",
        data={
            "AdminID": admin_db.AdminID,
            "Username": admin_db.Username,
            "Role": admin_db.RoleID,
            "last_login": (
                admin_db.LastLogin.isoformat() if admin_db.LastLogin else None
            ),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    )


def get_all_admins(
    db: Session,
    current_admin_id: int,  # Use current_admin.AdminID
    page: int = 1,
    per_page: int = 10,
    username: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[str] = None,
    sort_by: Optional[AdminSortBy] = None,
    order: Optional[AdminOrder] = None,
):
    query = db.query(Admin)

    # Filtering
    if username:
        query = query.filter(Admin.Username.ilike(f"%{username}%"))
    if email:
        query = query.filter(Admin.Email.ilike(f"%{email}%"))
    if role:
        query = query.filter(Admin.Role == role)

    # Sorting
    sort_column = {
        AdminSortBy.admin_id: Admin.AdminID,
        AdminSortBy.username: Admin.Username,
        AdminSortBy.email: Admin.Email,
        AdminSortBy.role: Admin.RoleID,
        AdminSortBy.created_at: Admin.CreatedAt,
        AdminSortBy.last_login: Admin.LastLogin,
    }.get(
        sort_by, Admin.AdminID
    )  # Default to AdminID
    query = query.order_by(
        asc(sort_column) if order == AdminOrder.asc else desc(sort_column)
    )

    # Pagination
    total_admins = query.count()
    admins = query.offset((page - 1) * per_page).limit(per_page).all()
    admin_data = [
        AdminResponseData.model_validate(admin).model_dump() for admin in admins
    ]

    return PaginatedResponse(
        success=True,
        message="Admins retrieved successfully",
        data={"admins": admin_data},
        page=page,
        per_page=per_page,
        total_items=total_admins,
        total_pages=(total_admins + per_page - 1) // per_page,
    )


def toggle_user_active_status(user_id: int, current_admin_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()

    if not user:
        return error_response(
            message="User not found", status_code=status.HTTP_404_NOT_FOUND
        )

    user.IsActive = not user.IsActive
    if user.IsActive:  # If activating, set the approving admin
        user.ApprovedByAdminID = current_admin_id
    else:  # If deactivating, clear the approving admin
        user.ApprovedByAdminID = None

    db.commit()
    return success_response(
        message=f"User status updated successfully. New status: {'Active' if user.IsActive else 'Inactive'}",
        data={
            "UserID": user.UserID,
            "IsActive": user.IsActive,
            "ApprovedByAdminID": user.ApprovedByAdminID,
        },
    )


def get_all_users(
    page: int,
    per_page: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    isactive: Optional[bool] = None,
    account_type: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    sort_by: Optional[SortBy] = None,
    order: Optional[Order] = None,
    db: Session = None,
):
    query = db.query(User)

    # Apply filters
    if username:
        query = query.filter(User.Username.ilike(f"%{username}%"))
    if email:
        query = query.filter(User.Email.ilike(f"%{email}%"))
    if account_type:
        query = query.filter(User.AccountType == account_type)
    if balance_min is not None:
        query = query.filter(User.Balance >= balance_min)
    if balance_max is not None:
        query = query.filter(User.Balance <= balance_max)
    if isactive is not None:
        query = query.filter(User.IsActive == isactive)

    # Apply sorting
    sort_field = {
        SortBy.user_id: User.UserID,
        SortBy.username: User.Username,
        SortBy.email: User.Email,
        SortBy.balance: User.Balance,
        SortBy.created_at: User.CreatedAt,
        SortBy.last_login: User.LastLogin,
    }.get(
        sort_by, User.UserID
    )  # Default to UserID if sort_by is invalid

    sort_order = desc if order == Order.desc else asc
    query = query.order_by(sort_order(sort_field))

    # Pagination
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Users retrieved successfully",
        data={
            "users": [UserResponseData.model_validate(u).model_dump() for u in users]
        },
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    ).model_dump()


def update_user(user_id: int, user_update: UserUpdate, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Check for unique constraints
    if user_update.Username and user_update.Username != user.Username:
        if db.query(User).filter(User.Username == user_update.Username).first():
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Username already exists",
            )
    if user_update.Email and user_update.Email != user.Email:
        if db.query(User).filter(User.Email == user_update.Email).first():
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, message="Email already exists"
            )

    # Handle password update if provided
    update_data = user_update.model_dump(exclude_unset=True)
    if "Password" in update_data:
        user.Password = pwd_context.hash(
            update_data.pop("Password")
        )  # Hash and remove from update_data

    # Apply updates (including IsActive for admins)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
        return success_response(
            message="User updated successfully",
            data=UserResponseData.model_validate(user).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update user",
            details={"error": str(e)},
        )


def delete_user(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Check for active loans
    active_loans = (
        db.query(Loan)
        .filter(Loan.UserID == user_id, Loan.LoanStatus.in_(["Pending", "Approved"]))
        .count()
    )
    if active_loans > 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Cannot delete user with {active_loans} active loan(s)",
        )

    # Optionally check for non-zero balance or active transactions
    if user.Balance != 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot delete user with non-zero balance",
        )

    try:
        db.delete(user)
        db.commit()
        return success_response(
            message="User deleted successfully", data={"UserID": user_id}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to delete user",
            details={"error": str(e)},
        )


def get_analytics_summary(db: Session):
    # Total Users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.IsActive == True).count()
    inactive_users = total_users - active_users

    # Total Transaction Volume
    deposit_total = (
        db.query(func.sum(Deposit.Amount))
        .filter(Deposit.Status == "Completed")
        .scalar()
        or 0
    )
    transfer_total = (
        db.query(func.sum(Transfer.Amount))
        .filter(Transfer.Status == "Completed")
        .scalar()
        or 0
    )
    withdrawal_total = (
        db.query(func.sum(Withdrawal.Amount))
        .filter(Withdrawal.Status == "Completed")
        .scalar()
        or 0
    )
    total_transaction_volume = float(deposit_total + transfer_total + withdrawal_total)

    # Total Loan Amounts
    total_loan_amount = (
        db.query(func.sum(Loan.LoanAmount))
        .filter(Loan.LoanStatus == "Approved")
        .scalar()
        or 0
    )
    total_loan_count = db.query(Loan).filter(Loan.LoanStatus == "Approved").count()

    # Pending Loans
    pending_loan_count = db.query(Loan).filter(Loan.LoanStatus == "Pending").count()
    pending_loan_amount = (
        db.query(func.sum(Loan.LoanAmount))
        .filter(Loan.LoanStatus == "Pending")
        .scalar()
        or 0
    )

    # Repaid Loans
    repaid_loan_count = db.query(Loan).filter(Loan.LoanStatus == "Repaid").count()

    # Average User Balance
    avg_user_balance = db.query(func.avg(User.Balance)).scalar() or 0

    return success_response(
        message="Analytics summary retrieved successfully",
        data={
            "users": {
                "total": total_users,
                "active": active_users,
                "inactive": inactive_users,
            },
            "transactions": {
                "total_volume": total_transaction_volume,
                "deposits": float(deposit_total),
                "transfers": float(transfer_total),
                "withdrawals": float(withdrawal_total),
            },
            "loans": {
                "total_approved_amount": float(total_loan_amount),
                "total_approved_count": total_loan_count,
                "pending_count": pending_loan_count,
                "pending_amount": float(pending_loan_amount),
                "repaid_count": repaid_loan_count,
            },
            "average_user_balance": float(avg_user_balance),
        },
    )


def export_transactions(
    db: Session,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_status: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    # Base query (similar to get_all_transactions)
    query = (
        db.query(
            func.coalesce(
                Deposit.DepositID, Transfer.TransferID, Withdrawal.WithdrawalID
            ).label("TransactionID"),
            User.Username.label("Username"),
            func.coalesce(Deposit.Amount, Transfer.Amount, Withdrawal.Amount).label(
                "Amount"
            ),
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status).label(
                "Status"
            ),
            func.coalesce(
                Deposit.Timestamp, Transfer.Timestamp, Withdrawal.Timestamp
            ).label("Timestamp"),
            case(
                (Deposit.DepositID.isnot(None), "Deposit"),
                (Transfer.TransferID.isnot(None), "Transfer"),
                (Withdrawal.WithdrawalID.isnot(None), "Withdrawal"),
            ).label("TransactionType"),
            Transfer.ReceiverID.label("ReceiverID"),
        )
        .outerjoin(Deposit, Deposit.UserID == User.UserID)
        .outerjoin(Transfer, Transfer.SenderID == User.UserID)
        .outerjoin(Withdrawal, Withdrawal.UserID == User.UserID)
        .filter(
            or_(
                Deposit.DepositID.isnot(None),
                Transfer.TransferID.isnot(None),
                Withdrawal.WithdrawalID.isnot(None),
            )
        )
    )

    # Apply filters
    if user_id:
        query = query.filter(User.UserID == user_id)
    if start_date:
        query = query.filter(
            func.coalesce(Deposit.Timestamp, Transfer.Timestamp, Withdrawal.Timestamp)
            >= start_date
        )
    if end_date:
        query = query.filter(
            func.coalesce(Deposit.Timestamp, Transfer.Timestamp, Withdrawal.Timestamp)
            <= end_date
        )
    if transaction_status:
        if transaction_status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction status value",
            )
        query = query.filter(
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status)
            == transaction_status
        )
    if transaction_type:
        if transaction_type not in ["Deposit", "Transfer", "Withdrawal"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type",
            )
        if transaction_type == "Deposit":
            query = query.filter(Deposit.DepositID.isnot(None))
        elif transaction_type == "Transfer":
            query = query.filter(Transfer.TransferID.isnot(None))
        elif transaction_type == "Withdrawal":
            query = query.filter(Withdrawal.WithdrawalID.isnot(None))

    # Execute query
    transactions = query.all()

    if not transactions:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No transactions found for export",
        )

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write headers
    headers = [
        "TransactionID",
        "Username",
        "Amount",
        "Status",
        "Timestamp",
        "TransactionType",
        "ReceiverUsername",
    ]
    writer.writerow(headers)

    # Fetch receiver usernames for transfers
    receiver_ids = {t.ReceiverID for t in transactions if t.ReceiverID}
    receivers = (
        db.query(User.UserID, User.Username).filter(User.UserID.in_(receiver_ids)).all()
    )
    receiver_map = {r.UserID: r.Username for r in receivers}

    # Write rows
    for t in transactions:
        receiver_username = receiver_map.get(t.ReceiverID, "") if t.ReceiverID else ""
        writer.writerow(
            [
                t.TransactionID,
                t.Username,
                f"{float(t.Amount):.2f}",
                t.Status,
                t.Timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                t.TransactionType,
                receiver_username,
            ]
        )

    # Prepare streaming response
    output.seek(0)
    filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
