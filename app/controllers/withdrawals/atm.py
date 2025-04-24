from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.withdrawal import Withdrawal
from app.models.card import Card
from app.models.user import User
from app.schemas.withdrawal_schema import WithdrawalCreate, WithdrawalResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.auth import pwd_context
from fastapi import status
import uuid
from fastapi import BackgroundTasks
from app.core.event_emitter import emit_event


async def create_withdrawal(
    withdrawal: WithdrawalCreate, db: Session, background_tasks: BackgroundTasks
):
    card = (
        db.query(Card)
        .filter(Card.CardNumber == withdrawal.CardNumber)
        .with_for_update()
        .first()
    )
    if not card:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="Card not found"
        )
    if card.Status != "Active":
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Card is not active"
        )
    if card.ExpirationDate < date.today():
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Card has expired"
        )

    if not pwd_context.verify(withdrawal.Pin, card.Pin):
        raise CustomHTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, message="Invalid PIN"
        )

    user = db.query(User).filter(User.UserID == card.UserID).with_for_update().first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )
    if not user.IsActive:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN, message="User account is inactive"
        )

    amount = Decimal(str(withdrawal.Amount))
    if amount <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Withdrawal amount must be positive",
        )
    if user.Balance < amount:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Insufficient balance"
        )

    new_withdrawal = Withdrawal(
        UserID=card.UserID,
        CardID=card.CardID,
        Amount=amount,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description="ATM withdrawal",
    )

    try:
        user.Balance -= amount
        new_withdrawal.Status = "Completed"
        db.add(new_withdrawal)
        db.commit()
        db.refresh(new_withdrawal)

        # Emit real-time notification
        await emit_event(
            "atm_withdrawal_completed",
            {
                "withdrawal_id": new_withdrawal.WithdrawalID,
                "amount": float(amount),
                "balance": float(user.Balance),
                "reference": new_withdrawal.ReferenceNumber,
                "CreatedAt": str(new_withdrawal.CreatedAt),
            },
            user_id=user.UserID,
            background_tasks=background_tasks,
        )

        return success_response(
            message="Withdrawal completed successfully",
            data=WithdrawalResponse.model_validate(new_withdrawal).model_dump(),
        )
    except Exception as e:
        db.rollback()
        new_withdrawal.Status = "Failed"
        db.commit()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Withdrawal failed",
            details={"error": str(e)},
        )
