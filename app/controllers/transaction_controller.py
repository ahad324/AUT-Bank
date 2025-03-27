from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, asc, desc
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
    # Verify sender exists and has sufficient balance
    sender = db.query(User).filter(User.UserID == sender_id).first()
    if not sender:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Sender not found",
            details={}
        )

    # Convert transaction.Amount to Decimal for comparison and arithmetic
    amount = Decimal(str(transaction.Amount))
    
    # Check balance for Withdrawal and Transfer
    if transaction.TransactionType in ["Transfer", "Withdrawal"] and sender.Balance < amount:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Insufficient balance",
            details={}
        )

    # Verify receiver exists for Transfer
    if transaction.TransactionType == "Transfer" and transaction.ReceiverID:
        receiver = db.query(User).filter(User.UserID == transaction.ReceiverID).first()
        if not receiver:
            raise CustomHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Receiver not found",
                details={}
            )

    # Create transaction with Status='Pending' (default in schema)
    new_transaction = Transaction(
        SenderID=sender_id if transaction.TransactionType in ["Transfer", "Withdrawal"] else None,
        ReceiverID=transaction.ReceiverID if transaction.TransactionType == "Transfer" else None,
        Amount=amount,
        TransactionType=transaction.TransactionType,
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",  # Matches table default
        Description=transaction.Description
    )

    try:
        # Update balances and set Status to 'Completed'
        if transaction.TransactionType == "Transfer":
            sender.Balance -= amount
            receiver.Balance += amount
        elif transaction.TransactionType == "Withdrawal":
            sender.Balance -= amount
        elif transaction.TransactionType == "Deposit":
            sender.Balance += amount
        # Loan Repayment will be handled in a future implementation

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
    # Base query: Transactions where user is Sender or Receiver
    query = db.query(Transaction).filter(
        or_(
            Transaction.SenderID == user_id,
            Transaction.ReceiverID == user_id
        )
    )

    # Apply filters
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

    # Total count for pagination
    total_items = query.count()

    # Apply sorting
    sort_column = {
        "Timestamp": Transaction.Timestamp,
        "Amount": Transaction.Amount
    }.get(sort_by, Transaction.Timestamp)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
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
        ).model_dump()

    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

def get_all_transactions(
    db: Session,
    page: int = 1,
    per_page: int = 10,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    sender_id: Optional[int] = None,
    receiver_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "Timestamp",
    order: Optional[str] = "desc"
):
    # Base query: All transactions
    query = db.query(Transaction)

    # Apply filters
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

    if sender_id:
        query = query.filter(Transaction.SenderID == sender_id)

    if receiver_id:
        query = query.filter(Transaction.ReceiverID == receiver_id)

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

    # Total count for pagination
    total_items = query.count()

    # Apply sorting
    sort_column = {
        "Timestamp": Transaction.Timestamp,
        "Amount": Transaction.Amount
    }.get(sort_by, Transaction.Timestamp)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
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
        ).model_dump()

    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

def get_user_transactions_for_admin(
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
    # Verify user exists
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    # Base query: Transactions where user is Sender or Receiver
    query = db.query(Transaction).filter(
        or_(
            Transaction.SenderID == user_id,
            Transaction.ReceiverID == user_id
        )
    )

    # Apply filters
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

    # Total count for pagination
    total_items = query.count()

    # Apply sorting
    sort_column = {
        "Timestamp": Transaction.Timestamp,
        "Amount": Transaction.Amount
    }.get(sort_by, Transaction.Timestamp)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    # Apply pagination
    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    if not transactions:
        return PaginatedResponse(
            success=True,
            message="No transactions found for this user",
            data={"transactions": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
        ).model_dump()

    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

def get_transaction_by_id(transaction_id: int, db: Session):
    transaction = db.query(Transaction).filter(Transaction.TransactionID == transaction_id).first()
    if not transaction:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Transaction not found"
        )

    return success_response(
        message="Transaction retrieved successfully",
        data=TransactionResponse.model_validate(transaction).model_dump()
    )