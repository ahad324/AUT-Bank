from fastapi import status, BackgroundTasks
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.transfer_schema import TransferCreate, TransferResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.event_emitter import emit_event
import uuid


async def create_transfer(sender_id: int, transfer: TransferCreate, db: Session,background_tasks:BackgroundTasks):
    sender = db.query(User).filter(User.UserID == sender_id).with_for_update().first()
    if not sender:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="Sender not found"
        )
    if not sender.IsActive:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN, message="Sender account is inactive"
        )

    amount = Decimal(str(transfer.Amount))
    if amount <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Amount must be positive"
        )
    if sender.Balance < amount:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Insufficient balance"
        )

    receiver = (
        db.query(User)
        .filter(User.UserID == transfer.ReceiverID)
        .with_for_update()
        .first()
    )
    if not receiver:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="Receiver not found"
        )
    if sender_id == transfer.ReceiverID:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Cannot transfer money to yourself",
        )
    if not receiver.IsActive:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Receiver account is inactive",
        )

    new_transfer = Transfer(
        SenderID=sender_id,
        ReceiverID=transfer.ReceiverID,
        Amount=amount,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=transfer.Description,
    )

    try:
        sender.Balance -= amount
        receiver.Balance += amount
        new_transfer.Status = "Completed"
        db.add(new_transfer)
        db.commit()
        db.refresh(new_transfer)

        # Emit notification to sender
        await emit_event(
            "money_sent",
            {
                "transfer_id": new_transfer.TransferID,
                "amount": float(amount),
                "receiver_id": receiver.UserID,
                "balance": float(sender.Balance),
                "reference": new_transfer.ReferenceNumber,
                "timestamp": str(new_transfer.Timestamp)
            },
            user_id=sender_id,
            background_tasks=background_tasks
        )

        # Emit notification to receiver
        await emit_event(
            "money_received",
            {
                "transfer_id": new_transfer.TransferID,
                "amount": float(amount),
                "sender_id": sender_id,
                "balance": float(receiver.Balance),
                "reference": new_transfer.ReferenceNumber,
                "timestamp": str(new_transfer.Timestamp)
            },
            user_id=receiver.UserID,
            background_tasks=background_tasks
        )

        return success_response(
            message="Transfer completed successfully",
            data=TransferResponse.model_validate(new_transfer).model_dump(),
        )
    except Exception as e:
        db.rollback()
        new_transfer.Status = "Failed"
        db.commit()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Transfer failed",
            details={"error": str(e)},
        )
