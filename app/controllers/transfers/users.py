from datetime import datetime, timezone
from fastapi import status, BackgroundTasks
from sqlalchemy.orm import Session
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.transfer_schema import TransferCreate, TransferResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from app.core.event_emitter import emit_event
import uuid


async def create_transfer(
    sender_id: int,
    transfer: TransferCreate,
    db: Session,
    background_tasks: BackgroundTasks,
):
    # Determine which identifier was provided and query accordingly
    receiver = None
    if transfer.cnic:
        receiver = db.query(User).filter(User.CNIC == transfer.cnic).first()
    elif transfer.username:
        receiver = db.query(User).filter(User.Username == transfer.username).first()
    elif transfer.email:
        receiver = db.query(User).filter(User.Email == transfer.email).first()

    if not receiver:
        raise CustomHTTPException(status_code=404, message="Receiver not found")

    if receiver.UserID == sender_id:
        raise CustomHTTPException(
            status_code=400, message="Cannot transfer to yourself"
        )

    if not receiver.IsActive:
        raise CustomHTTPException(
            status_code=400, message="Receiver account is inactive"
        )

    sender = db.query(User).filter(User.UserID == sender_id).first()
    if not sender or not sender.IsActive:
        raise CustomHTTPException(
            status_code=400, message="Sender account is invalid or inactive"
        )

    if sender.Balance < transfer.Amount:
        raise CustomHTTPException(status_code=400, message="Insufficient balance")

    if transfer.Amount <= 0:
        raise CustomHTTPException(
            status_code=400, message="Amount must be greater than zero"
        )

    new_transfer = Transfer(
        SenderID=sender_id,
        ReceiverID=receiver.UserID,
        Amount=transfer.Amount,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=transfer.Description,
        Timestamp=datetime.now(timezone.utc),
    )

    try:
        # Update balances
        sender.Balance -= transfer.Amount
        receiver.Balance += transfer.Amount
        new_transfer.Status = "Completed"

        db.add(new_transfer)
        db.commit()
        db.refresh(new_transfer)

        # Emit notification to sender
        await emit_event(
            "money_sent",
            {
                "transfer_id": new_transfer.TransferID,
                "amount": float(transfer.Amount),
                "receiver_id": receiver.UserID,
                "balance": float(sender.Balance),
                "reference": new_transfer.ReferenceNumber,
                "timestamp": str(new_transfer.Timestamp),
            },
            user_id=sender_id,
            background_tasks=background_tasks,
        )

        # Emit notification to receiver
        await emit_event(
            "money_received",
            {
                "transfer_id": new_transfer.TransferID,
                "amount": float(transfer.Amount),
                "sender_id": sender_id,
                "balance": float(receiver.Balance),
                "reference": new_transfer.ReferenceNumber,
                "timestamp": str(new_transfer.Timestamp),
            },
            user_id=receiver.UserID,
            background_tasks=background_tasks,
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
            status_code=500,
            message="Transfer failed",
            details={"error": str(e)},
        )
