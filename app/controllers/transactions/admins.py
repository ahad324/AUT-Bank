from sqlalchemy.orm import Session
from sqlalchemy import Transaction, or_, asc, desc, union_all
from app.models.transfer import Transfer
from app.models.deposit import Deposit
from app.models.user import User
from app.models.withdrawal import Withdrawal
from app.schemas.transfer_schema import TransferResponse
from app.schemas.deposit_schema import DepositResponse
from app.schemas.withdrawal_schema import WithdrawalResponse
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional, Union

def get_all_transactions(
    db: Session,
    page: int = 1,
    per_page: int = 10,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,  # Replaces sender_id/receiver_id for broader filtering
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "Timestamp",
    order: Optional[str] = "desc"
):
    # Define base queries for each type
    transfer_query = db.query(Transfer).select_from(Transfer).add_columns(
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
    deposit_query = db.query(Deposit).select_from(Deposit).add_columns(
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
    withdrawal_query = db.query(Withdrawal).select_from(Withdrawal).add_columns(
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

    # Apply filters
    if transaction_type:
        if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type")
        if transaction_type == "Transfer":
            query = transfer_query
        elif transaction_type == "Deposit":
            query = deposit_query
        elif transaction_type == "Withdrawal":
            query = withdrawal_query
    else:
        query = union_all(transfer_query, deposit_query, withdrawal_query)

    if status:
        if status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status")
        if transaction_type:
            query = query.filter_by(Status=status)
        else:
            query = query.filter(Transaction.Status == status)  # Adjust for union

    if user_id:
        if transaction_type == "Transfer":
            query = query.filter(or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id))
        elif transaction_type == "Deposit":
            query = query.filter(Deposit.UserID == user_id)
        elif transaction_type == "Withdrawal":
            query = query.filter(Withdrawal.UserID == user_id)
        else:
            query = query.filter(or_(
                Transfer.SenderID == user_id,
                Transfer.ReceiverID == user_id,
                Deposit.UserID == user_id,
                Withdrawal.UserID == user_id
            ))

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

    # Map results to appropriate response schemas
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
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

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
            message="No transactions found for this user",
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

def get_transaction_by_id(transaction_type: str, transaction_id: int, db: Session):
    if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type")

    if transaction_type == "Transfer":
        transaction = db.query(Transfer).filter(Transfer.TransferID == transaction_id).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Transfer not found")
        return success_response(
            message="Transfer retrieved successfully",
            data=TransferResponse.model_validate(transaction).model_dump()
        )
    elif transaction_type == "Deposit":
        transaction = db.query(Deposit).filter(Deposit.DepositID == transaction_id).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Deposit not found")
        return success_response(
            message="Deposit retrieved successfully",
            data=DepositResponse.model_validate(transaction).model_dump()
        )
    elif transaction_type == "Withdrawal":
        transaction = db.query(Withdrawal).filter(Withdrawal.WithdrawalID == transaction_id).first()
        if not transaction:
            raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Withdrawal not found")
        return success_response(
            message="Withdrawal retrieved successfully",
            data=WithdrawalResponse.model_validate(transaction).model_dump()
        )    
        
        