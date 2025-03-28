from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction_schema import TransactionResponse
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional

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
    query = db.query(Transaction)

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
        paginated_response = PaginatedResponse(
            success=True,
            message="No transactions found",
            data={"transactions": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
        ).model_dump()
        return success_response(
            message=paginated_response["message"],
            data=paginated_response
        )

    total_pages = (total_items + per_page - 1) // per_page

    paginated_response = PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

    return success_response(
        message=paginated_response["message"],
        data=paginated_response
    )

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
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

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
        paginated_response = PaginatedResponse(
            success=True,
            message="No transactions found for this user",
            data={"transactions": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
        ).model_dump()
        return success_response(
            message=paginated_response["message"],
            data=paginated_response
        )

    total_pages = (total_items + per_page - 1) // per_page

    paginated_response = PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

    return success_response(
        message=paginated_response["message"],
        data=paginated_response
    )

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