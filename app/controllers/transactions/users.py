from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc, union_all
from app.models.deposit import Deposit
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.models.withdrawal import Withdrawal
from app.schemas.deposit_schema import DepositResponse
from app.schemas.transaction_schema import TransactionCreate, TransactionResponse
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional

from app.schemas.transfer_schema import TransferCreate, TransferResponse
from app.schemas.withdrawal_schema import WithdrawalResponse

def create_transfer(sender_id: int, transfer: TransferCreate, db: Session):
    sender = db.query(User).filter(User.UserID == sender_id).with_for_update().first()
    if not sender:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Sender not found")
    if not sender.IsActive:
        raise CustomHTTPException(status_code=status.HTTP_403_FORBIDDEN, message="Sender account is inactive")

    amount = Decimal(str(transfer.Amount))
    if amount <= 0:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Amount must be positive")
    if sender.Balance < amount:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Insufficient balance")

    receiver = db.query(User).filter(User.UserID == transfer.ReceiverID).with_for_update().first()
    if not receiver:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Receiver not found")
    if sender_id == transfer.ReceiverID:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Cannot transfer money to yourself")
    if not receiver.IsActive:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Receiver account is inactive")

    new_transfer = Transfer(
        SenderID=sender_id,
        ReceiverID=transfer.ReceiverID,
        Amount=amount,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=transfer.Description
    )

    try:
        sender.Balance -= amount
        receiver.Balance += amount
        new_transfer.Status = "Completed"
        db.add(new_transfer)
        db.commit()
        db.refresh(new_transfer)
        return success_response(
            message="Transfer completed successfully",
            data=TransferResponse.model_validate(new_transfer).model_dump()
        )
    except Exception as e:
        db.rollback()
        new_transfer.Status = "Failed"
        db.commit()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Transfer failed",
            details={"error": str(e)}
        )

def get_user_transactions(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "Timestamp",
    order: Optional[str] = "desc"
):
    if transaction_type:
        if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type")
        if transaction_type == "Transfer":
            query = db.query(Transfer).filter(or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id))
        elif transaction_type == "Deposit":
            query = db.query(Deposit).filter(Deposit.UserID == user_id)
        elif transaction_type == "Withdrawal":
            query = db.query(Withdrawal).filter(Withdrawal.UserID == user_id)
    else:
        transfer_query = db.query(Transfer).filter(or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id)).add_columns(
            Transfer.TransferID.label("ID"),
            Transfer.SenderID.label("UserID"),
            Transfer.ReceiverID.label("RelatedUserID"),
            Transfer.Amount,
            "Transfer".label("TransactionType"),
            Transfer.ReferenceNumber,
            Transfer.Status,
            Transfer.Description,
            Transfer.Timestamp
        )
        deposit_query = db.query(Deposit).filter(Deposit.UserID == user_id).add_columns(
            Deposit.DepositID.label("ID"),
            Deposit.UserID.label("UserID"),
            Deposit.AdminID.label("RelatedUserID"),
            Deposit.Amount,
            "Deposit".label("TransactionType"),
            Deposit.ReferenceNumber,
            Deposit.Status,
            Deposit.Description,
            Deposit.Timestamp
        )
        withdrawal_query = db.query(Withdrawal).filter(Withdrawal.UserID == user_id).add_columns(
            Withdrawal.WithdrawalID.label("ID"),
            Withdrawal.UserID.label("UserID"),
            Withdrawal.CardID.label("RelatedUserID"),
            Withdrawal.Amount,
            "Withdrawal".label("TransactionType"),
            Withdrawal.ReferenceNumber,
            Withdrawal.Status,
            Withdrawal.Description,
            Withdrawal.Timestamp
        )
        query = union_all(transfer_query, deposit_query, withdrawal_query)

    if status:
        if status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status")
        if transaction_type:
            query = query.filter_by(Status=status)
        else:
            query = query.filter(Transaction.Status == status)

    if start_date and end_date:
        if start_date > end_date:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="start_date must be before end_date")
        query = query.filter(Transaction.Timestamp.between(start_date, end_date))
    elif start_date:
        query = query.filter(Transaction.Timestamp >= start_date)
    elif end_date:
        query = query.filter(Transaction.Timestamp <= end_date)

    total_items = query.count()

    sort_column = {"Timestamp": "Timestamp", "Amount": "Amount"}.get(sort_by, "Timestamp")
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    if not transactions:
        return PaginatedResponse(
            success=True,
            message="No transactions found",
            data={"transactions": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
        )

    total_pages = (total_items + per_page - 1) // per_page

    transaction_list = []
    for t in transactions:
        if t.TransactionType == "Transfer":
            transaction_list.append(TransferResponse(
                TransferID=t.ID,
                SenderID=t.UserID,
                ReceiverID=t.RelatedUserID,
                Amount=t.Amount,
                ReferenceNumber=t.ReferenceNumber,
                Status=t.Status,
                Description=t.Description,
                Timestamp=str(t.Timestamp)
            ).model_dump())
        elif t.TransactionType == "Deposit":
            transaction_list.append(DepositResponse(
                DepositID=t.ID,
                UserID=t.UserID,
                AdminID=t.RelatedUserID,
                Amount=t.Amount,
                ReferenceNumber=t.ReferenceNumber,
                Status=t.Status,
                Description=t.Description,
                Timestamp=str(t.Timestamp)
            ).model_dump())
        elif t.TransactionType == "Withdrawal":
            transaction_list.append(WithdrawalResponse(
                WithdrawalID=t.ID,
                UserID=t.UserID,
                CardID=t.RelatedUserID,
                Amount=t.Amount,
                ReferenceNumber=t.ReferenceNumber,
                Status=t.Status,
                Description=t.Description,
                Timestamp=str(t.Timestamp)
            ).model_dump())

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": transaction_list},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    )
    
def get_user_transaction_by_id(user_id: int, transaction_type: str, transaction_id: int, db: Session):
    if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type")

    if transaction_type == "Transfer":
        transaction = db.query(Transfer).filter(
            Transfer.TransferID == transaction_id,
            or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id)
        ).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Transfer not found or not associated with this user")
        return success_response(
            message="Transfer retrieved successfully",
            data=TransferResponse.model_validate(transaction).model_dump()
        )
    elif transaction_type == "Deposit":
        transaction = db.query(Deposit).filter(
            Deposit.DepositID == transaction_id,
            Deposit.UserID == user_id
        ).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Deposit not found or not associated with this user")
        return success_response(
            message="Deposit retrieved successfully",
            data=DepositResponse.model_validate(transaction).model_dump()
        )
    elif transaction_type == "Withdrawal":
        transaction = db.query(Withdrawal).filter(
            Withdrawal.WithdrawalID == transaction_id,
            Withdrawal.UserID == user_id
        ).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Withdrawal not found or not associated with this user")
        return success_response(
            message="Withdrawal retrieved successfully",
            data=WithdrawalResponse.model_validate(transaction).model_dump()
        )    