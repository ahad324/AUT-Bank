from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.deposit import Deposit
from app.models.user import User
from app.schemas.deposit_schema import DepositCreate, DepositResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.event_emitter import emit_event  # Add this import
from fastapi import status
import uuid
from fastapi import BackgroundTasks


async def create_deposit(
    user_id: int, 
    admin_id: int, 
    deposit: DepositCreate, 
    db: Session,
    background_tasks: BackgroundTasks
):
    user = db.query(User).filter(User.UserID == user_id).with_for_update().first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            message="User not found"
        )

    amount = Decimal(str(deposit.Amount))
    if amount <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Deposit amount must be positive",
        )

    new_deposit = Deposit(
        UserID=user_id,
        AdminID=admin_id,
        Amount=amount,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=deposit.Description or "Admin-initiated deposit",
    )

    try:
        user.Balance += amount
        new_deposit.Status = "Completed"
        db.add(new_deposit)
        db.commit()
        db.refresh(new_deposit)

        # Emit real-time notification to user
        await emit_event(
            "deposit_completed",
            {
                "amount": float(amount),
                "balance": float(user.Balance),
                "reference": new_deposit.ReferenceNumber,
                "timestamp": str(new_deposit.Timestamp)
            },
            user_id=user_id,
            background_tasks=background_tasks
        )

        # Notify admins about the deposit
        await emit_event(
            "deposit_processed",
            {
                "user_id": user_id,
                "amount": float(amount),
                "admin_id": admin_id,
                "reference": new_deposit.ReferenceNumber
            },
            broadcast=True,
            background_tasks=background_tasks
        )

        return success_response(
            message="Deposit completed successfully",
            data=DepositResponse.model_validate(new_deposit).model_dump(),
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Deposit failed",
            details={"error": str(e)},
        )
