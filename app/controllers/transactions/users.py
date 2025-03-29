from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction_schema import TransactionCreate, TransactionResponse
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional

def create_transaction(sender_id: int, transaction: TransactionCreate, db: Session):
    sender = db.query(User).filter(User.UserID == sender_id).with_for_update().first()
    if not sender:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Sender not found",
            details={}
        )

    amount = Decimal(str(transaction.Amount))
    
    if transaction.TransactionType in ["Transfer", "Withdrawal"] and sender.Balance < amount:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Insufficient balance",
            details={}
        )

    if transaction.TransactionType == "Transfer" and transaction.ReceiverID:
        receiver = db.query(User).filter(User.UserID == transaction.ReceiverID).with_for_update().first()
        if not receiver:
            raise CustomHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Receiver not found",
                details={}
            )
        if sender_id == transaction.ReceiverID:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Cannot transfer money to yourself",
                details={}
            )

    new_transaction = Transaction(
        SenderID=sender_id,
        ReceiverID=transaction.ReceiverID if transaction.TransactionType == "Transfer" else None,
        Amount=amount,
        TransactionType=transaction.TransactionType,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=transaction.Description
    )

    try:
        if transaction.TransactionType == "Transfer":
            sender.Balance -= amount
            receiver.Balance += amount
        elif transaction.TransactionType == "Withdrawal":
            sender.Balance -= amount
        elif transaction.TransactionType == "Deposit":
            sender.Balance += amount

        new_transaction.Status = "Completed"
        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)

        return success_response(
            message=f"{transaction.TransactionType} completed successfully",
            data=TransactionResponse.model_validate(new_transaction).model_dump()
        )
    except Exception as e:
        db.rollback()
        new_transaction.Status = "Failed"
        db.commit()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"{transaction.TransactionType} failed",
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
    query = db.query(Transaction).filter(
        or_(
            Transaction.SenderID == user_id,
            Transaction.ReceiverID == user_id
        )
    )

    if transaction_type:
        if transaction_type not in ["Deposit", "Withdrawal", "Transfer"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type"
            )
        query = query.filter(Transaction.TransactionType == transaction_type)

    if status:
        if status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid status"
            )
        query = query.filter(Transaction.Status == status)

    if start_date and end_date:
        if start_date > end_date:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="start_date must be before end_date"
            )
        query = query.filter(Transaction.Timestamp.between(start_date, end_date))
    elif start_date:
        query = query.filter(Transaction.Timestamp >= start_date)
    elif end_date:
        query = query.filter(Transaction.Timestamp <= end_date)

    total_items = query.count()

    sort_column = {
        "Timestamp": Transaction.Timestamp,
        "Amount": Transaction.Amount
    }.get(sort_by, Transaction.Timestamp)
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

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    )
def get_user_transaction_by_id(user_id: int, transaction_id: int, db: Session):
    transaction = db.query(Transaction).filter(
        Transaction.TransactionID == transaction_id,
        or_(
            Transaction.SenderID == user_id,
            Transaction.ReceiverID == user_id
        )
    ).first()
    if not transaction:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found or not associated with this user",
            details={}
        )
    return success_response(
        message="Transaction retrieved successfully",
        data=TransactionResponse.model_validate(transaction).model_dump()
    )