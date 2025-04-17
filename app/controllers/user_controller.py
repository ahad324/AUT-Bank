from io import StringIO
import csv
from typing import Optional
from fastapi.responses import StreamingResponse
from fastapi import Depends, status
from sqlalchemy.orm import Session, aliased
from app.core.exceptions import CustomHTTPException, DatabaseError
from app.core.rate_limiter import CACHE_TTL_SHORT, get_redis_client
from app.schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserPasswordUpdate,
    UserResponseData,
    LoginResponseData,
    UserUpdate,
)
from app.models.user import User
from app.core.database import get_db
from app.core.responses import success_response
from app.core.utils import hash_password, check_unique_field
from app.core.auth import create_access_token, create_refresh_token
from passlib.context import CryptContext
from datetime import datetime, timezone
from sqlalchemy import case, func, or_
from app.models.deposit import Deposit
from app.models.transfer import Transfer
from app.models.withdrawal import Withdrawal
from app.models.loan import Loan

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def check_field_uniqueness(
    field: str,
    value: str,
    db: Session,
):
    if field not in ["Email", "CNIC", "Username"]:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid field. Must be Email, CNIC, or Username",
        )

    # Check cache first
    redis_client = get_redis_client()
    cache_key = f"uniqueness:{field}:{value}"
    cached_result = redis_client.get(cache_key)
    if cached_result:
        return success_response(
            message=f"{field} availability checked from cache",
            data={"is_unique": cached_result == "true"},
        )

    # Query database
    exists = db.query(User).filter(getattr(User, field) == value).first() is not None

    redis_client.setex(cache_key, CACHE_TTL_SHORT, "false" if exists else "true")

    return success_response(
        message=f"{field} availability checked", data={"is_unique": not exists}
    )


def register_user(user: UserCreate, db: Session = Depends(get_db)):
    for field in ["Email", "CNIC", "Username"]:
        check_unique_field(db, User, field, getattr(user, field))

    try:
        new_user = User(**user.model_dump(exclude={"Password"}))
        new_user.Password = hash_password(user.Password)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return success_response(
            message="User registered successfully, pending admin approval",
            data=UserResponseData.model_validate(new_user).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Database error: {str(e)}")


def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(
            (User.Email == credentials.login_id)
            | (User.Username == credentials.login_id)
        )
        .first()
    )

    if not user or not pwd_context.verify(credentials.Password, user.Password):
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, message="Invalid credentials"
        )

    if not user.IsActive:  # ✅ Prevent login if inactive
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN, message="Account is pending approval"
        )

    user.LastLogin = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": str(user.UserID), "role_id": 0})
    refresh_token = create_refresh_token(data={"sub": str(user.UserID), "role_id": 0})
    return success_response(
        message="Login successful",
        data={
            **LoginResponseData.model_validate(user).model_dump(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
    )


def update_current_user(user_id: int, user_update: UserUpdate, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Prevent users from updating sensitive fields
    restricted_fields = {"IsActive", "Balance", "Password", "AccountType"}
    if any(
        field in restricted_fields
        for field in user_update.model_dump(exclude_unset=True).keys()
    ):
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Cannot update restricted fields (e.g., IsActive, Balance, Password) via this endpoint. Use /me/password for password changes.",
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

    # Apply updates
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
        return success_response(
            message="Profile updated successfully",
            data=UserResponseData.model_validate(user).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update profile",
            details={"error": str(e)},
        )


def update_user_password(
    user_id: int, password_update: UserPasswordUpdate, db: Session
):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    # Verify current password
    if not pwd_context.verify(password_update.CurrentPassword, user.Password):
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Current password is incorrect",
        )

    # Update password
    user.Password = pwd_context.hash(password_update.NewPassword)

    try:
        db.commit()
        db.refresh(user)
        return success_response(
            message="Password updated successfully", data={"UserID": user.UserID}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update password",
            details={"error": str(e)},
        )


def get_user_profile(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )
    return success_response(
        message="User details retrieved successfully",
        data=UserResponseData(
            UserID=user.UserID,
            Username=user.Username,
            FirstName=user.FirstName,
            LastName=user.LastName,
            StreetAddress=user.StreetAddress,
            City=user.City,
            State=user.State,
            Country=user.Country,
            PostalCode=user.PostalCode,
            PhoneNumber=user.PhoneNumber,
            CNIC=user.CNIC,
            Email=user.Email,
            AccountType=user.AccountType,
            Balance=user.Balance,
            IsActive=user.IsActive,
            DateOfBirth=user.DateOfBirth.isoformat() if user.DateOfBirth else None,
            CreatedAt=user.CreatedAt.isoformat() if user.CreatedAt else None,
            LastLogin=user.LastLogin.isoformat() if user.LastLogin else None,
            access_token="",
            refresh_token="",
            token_type="bearer",
        ).model_dump(exclude={"access_token", "refresh_token"}),
    )


def get_user_analytics_summary(user_id: int, db: Session):
    # Total Transactions
    deposit_count = (
        db.query(Deposit)
        .filter(Deposit.UserID == user_id, Deposit.Status == "Completed")
        .count()
    )
    deposit_total = (
        db.query(func.sum(Deposit.Amount))
        .filter(Deposit.UserID == user_id, Deposit.Status == "Completed")
        .scalar()
        or 0
    )

    transfer_sent_count = (
        db.query(Transfer)
        .filter(Transfer.SenderID == user_id, Transfer.Status == "Completed")
        .count()
    )
    transfer_sent_total = (
        db.query(func.sum(Transfer.Amount))
        .filter(Transfer.SenderID == user_id, Transfer.Status == "Completed")
        .scalar()
        or 0
    )

    transfer_received_count = (
        db.query(Transfer)
        .filter(Transfer.ReceiverID == user_id, Transfer.Status == "Completed")
        .count()
    )
    transfer_received_total = (
        db.query(func.sum(Transfer.Amount))
        .filter(Transfer.ReceiverID == user_id, Transfer.Status == "Completed")
        .scalar()
        or 0
    )

    withdrawal_count = (
        db.query(Withdrawal)
        .filter(Withdrawal.UserID == user_id, Withdrawal.Status == "Completed")
        .count()
    )
    withdrawal_total = (
        db.query(func.sum(Withdrawal.Amount))
        .filter(Withdrawal.UserID == user_id, Withdrawal.Status == "Completed")
        .scalar()
        or 0
    )

    total_transaction_count = (
        deposit_count + transfer_sent_count + transfer_received_count + withdrawal_count
    )
    total_transaction_volume = float(
        deposit_total + transfer_sent_total + transfer_received_total + withdrawal_total
    )

    # Average Transaction Amount
    avg_transaction_amount = (
        total_transaction_volume / total_transaction_count
        if total_transaction_count > 0
        else 0
    )

    # Total Loan Amounts
    total_loan_amount = (
        db.query(func.sum(Loan.LoanAmount))
        .filter(Loan.UserID == user_id, Loan.LoanStatus == "Approved")
        .scalar()
        or 0
    )
    total_loan_count = (
        db.query(Loan)
        .filter(Loan.UserID == user_id, Loan.LoanStatus == "Approved")
        .count()
    )

    # Pending Loans
    pending_loan_count = (
        db.query(Loan)
        .filter(Loan.UserID == user_id, Loan.LoanStatus == "Pending")
        .count()
    )

    # Current Balance
    user = db.query(User).filter(User.UserID == user_id).first()
    current_balance = float(user.Balance) if user else 0

    return success_response(
        message="User analytics summary retrieved successfully",
        data={
            "transactions": {
                "total_count": total_transaction_count,
                "total_volume": total_transaction_volume,
                "deposits": {
                    "count": deposit_count,
                    "amount": float(deposit_total),
                },
                "transfers_sent": {
                    "count": transfer_sent_count,
                    "amount": float(transfer_sent_total),
                },
                "transfers_received": {
                    "count": transfer_received_count,
                    "amount": float(transfer_received_total),
                },
                "withdrawals": {
                    "count": withdrawal_count,
                    "amount": float(withdrawal_total),
                },
                "average_amount": float(avg_transaction_amount),
            },
            "loans": {
                "total_approved_amount": float(total_loan_amount),
                "total_approved_count": total_loan_count,
                "pending_count": pending_loan_count,
            },
            "current_balance": current_balance,
        },
    )


def export_user_transactions(
    user_id: int,
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_status: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    # Alias the Transfers table for sent and received transactions
    TransfersSent = aliased(Transfer, name="TransfersSent")
    TransfersReceived = aliased(Transfer, name="TransfersReceived")

    # Start query from User table to avoid ambiguity
    query = (
        db.query(User)  # Start with User as the base table
        .filter(User.UserID == user_id)
        .outerjoin(Deposit, Deposit.UserID == User.UserID)
        .outerjoin(TransfersSent, TransfersSent.SenderID == User.UserID)
        .outerjoin(TransfersReceived, TransfersReceived.ReceiverID == User.UserID)
        .outerjoin(Withdrawal, Withdrawal.UserID == User.UserID)
        .with_entities(
            func.coalesce(
                Deposit.DepositID,
                TransfersSent.TransferID,
                TransfersReceived.TransferID,
                Withdrawal.WithdrawalID,
            ).label("TransactionID"),
            func.coalesce(
                Deposit.Amount,
                TransfersSent.Amount,
                TransfersReceived.Amount,
                Withdrawal.Amount,
            ).label("Amount"),
            func.coalesce(
                Deposit.Status,
                TransfersSent.Status,
                TransfersReceived.Status,
                Withdrawal.Status,
            ).label("Status"),
            func.coalesce(
                Deposit.Timestamp,
                TransfersSent.Timestamp,
                TransfersReceived.Timestamp,
                Withdrawal.Timestamp,
            ).label("Timestamp"),
            case(
                (Deposit.DepositID.isnot(None), "Deposit"),
                (TransfersSent.TransferID.isnot(None), "Transfer (Sent)"),
                (TransfersReceived.TransferID.isnot(None), "Transfer (Received)"),
                (Withdrawal.WithdrawalID.isnot(None), "Withdrawal"),
            ).label("TransactionType"),
            func.coalesce(TransfersSent.ReceiverID, TransfersReceived.ReceiverID).label(
                "ReceiverID"
            ),
        )
        .filter(
            or_(
                Deposit.DepositID.isnot(None),
                TransfersSent.TransferID.isnot(None),
                TransfersReceived.TransferID.isnot(None),
                Withdrawal.WithdrawalID.isnot(None),
            )
        )
    )

    # Apply filters
    if start_date:
        query = query.filter(
            func.coalesce(
                Deposit.Timestamp,
                TransfersSent.Timestamp,
                TransfersReceived.Timestamp,
                Withdrawal.Timestamp,
            )
            >= start_date
        )
    if end_date:
        query = query.filter(
            func.coalesce(
                Deposit.Timestamp,
                TransfersSent.Timestamp,
                TransfersReceived.Timestamp,
                Withdrawal.Timestamp,
            )
            <= end_date
        )
    if transaction_status:
        if transaction_status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction status value",
            )
        query = query.filter(
            func.coalesce(
                Deposit.Status,
                TransfersSent.Status,
                TransfersReceived.Status,
                Withdrawal.Status,
            )
            == transaction_status
        )
    if transaction_type:
        if transaction_type not in [
            "Deposit",
            "Transfer (Sent)",
            "Transfer (Received)",
            "Withdrawal",
        ]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type value",
            )
        if transaction_type == "Deposit":
            query = query.filter(Deposit.DepositID.isnot(None))
        elif transaction_type == "Transfer (Sent)":
            query = query.filter(TransfersSent.TransferID.isnot(None))
        elif transaction_type == "Transfer (Received)":
            query = query.filter(TransfersReceived.TransferID.isnot(None))
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
                f"{float(t.Amount):.2f}",
                t.Status,
                t.Timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                t.TransactionType,
                receiver_username,
            ]
        )

    # Prepare streaming response
    output.seek(0)
    filename = f"my_transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
