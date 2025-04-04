from fastapi import Depends, status
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException, DatabaseError
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
from app.core.responses import success_response, error_response
from app.core.auth import create_access_token, create_refresh_token
from passlib.context import CryptContext
from datetime import datetime, timezone
from sqlalchemy import func
from app.models.deposit import Deposit
from app.models.transfer import Transfer
from app.models.withdrawal import Withdrawal
from app.models.loan import Loan

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User)
        .filter(
            (User.Email == user.Email)
            | (User.CNIC == user.CNIC)
            | (User.Username == user.Username)
        )
        .first()
    )

    if existing_user:
        field = (
            "Email"
            if existing_user.Email == user.Email
            else "CNIC" if existing_user.CNIC == user.CNIC else "Username"
        )
        return error_response(
            message=f"{field} already registered",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        new_user = User(**user.model_dump(exclude={"Password"}))
        new_user.Password = pwd_context.hash(user.Password)

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
        return error_response(
            message="Invalid credentials", status_code=status.HTTP_401_UNAUTHORIZED
        )

    if not user.IsActive:  # ✅ Prevent login if inactive
        return error_response(
            message="Account is pending approval", status_code=status.HTTP_403_FORBIDDEN
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
