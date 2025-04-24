from sqlalchemy.orm import Session
from sqlalchemy import func, case, or_
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_, asc, desc
from app.models.transfer import Transfer
from app.models.deposit import Deposit
from app.models.user import User
from app.models.withdrawal import Withdrawal

from app.schemas.transactions_schema import TransactionResponse
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional


def get_user_transactions(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    transaction_type: Optional[str] = None,
    transaction_status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc",
):
    # Validate inputs
    if transaction_type and transaction_type not in [
        "Deposit",
        "Transfer",
        "Withdrawal",
    ]:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type"
        )
    if transaction_status and transaction_status not in [
        "Pending",
        "Completed",
        "Failed",
    ]:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid transaction status",
        )

    # Alias for Receiver User table
    Receiver = aliased(User)

    # Unified query for all transaction types
    query = (
        db.query(
            func.coalesce(
                Deposit.DepositID, Transfer.TransferID, Withdrawal.WithdrawalID
            ).label("TransactionID"),
            User.UserID.label("UserID"),
            User.Username.label("Username"),
            func.coalesce(Deposit.Amount, Transfer.Amount, Withdrawal.Amount).label(
                "Amount"
            ),
            case(
                (Deposit.DepositID.isnot(None), "Deposit"),
                (Transfer.TransferID.isnot(None), "Transfer"),
                (Withdrawal.WithdrawalID.isnot(None), "Withdrawal"),
            ).label("TransactionType"),
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status).label(
                "Status"
            ),
            func.coalesce(
                Deposit.Description, Transfer.Description, Withdrawal.Description
            ).label("Description"),
            func.coalesce(
                Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt
            ).label("CreatedAt"),
            func.coalesce(
                Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt
            ).label("UpdatedAt"),
            Transfer.ReceiverID.label("ReceiverID"),
            Receiver.Username.label("ReceiverUsername"),
        )
        .select_from(User)
        .outerjoin(Deposit, Deposit.UserID == User.UserID)
        .outerjoin(
            Transfer,
            (Transfer.SenderID == User.UserID) | (Transfer.ReceiverID == User.UserID),
        )
        .outerjoin(Withdrawal, Withdrawal.UserID == User.UserID)
        .outerjoin(Receiver, Receiver.UserID == Transfer.ReceiverID)
        .filter(
            or_(
                Deposit.UserID == user_id,
                Transfer.SenderID == user_id,
                Transfer.ReceiverID == user_id,
                Withdrawal.UserID == user_id,
            )
        )
    )

    # Apply filters
    if transaction_type:
        if transaction_type == "Deposit":
            query = query.filter(Deposit.DepositID.isnot(None))
        elif transaction_type == "Transfer":
            query = query.filter(Transfer.TransferID.isnot(None))
        elif transaction_type == "Withdrawal":
            query = query.filter(Withdrawal.WithdrawalID.isnot(None))
    if transaction_status:
        query = query.filter(
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status)
            == transaction_status
        )
    if start_date:
        query = query.filter(
            func.coalesce(Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt)
            >= start_date
        )
    if end_date:
        query = query.filter(
            func.coalesce(Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt)
            <= end_date
        )

    # Sorting
    sort_field_map = {
        "TransactionID": func.coalesce(
            Deposit.DepositID, Transfer.TransferID, Withdrawal.WithdrawalID
        ),
        "Amount": func.coalesce(Deposit.Amount, Transfer.Amount, Withdrawal.Amount),
        "CreatedAt": func.coalesce(
            Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt
        ),
        "Status": func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status),
    }
    sort_field = sort_field_map.get(sort_by, sort_field_map["CreatedAt"])
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_field))

    # Pagination
    total_items = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()

    # Format response using TransactionResponse
    transaction_list = [
        TransactionResponse(
            TransactionID=t.TransactionID,
            UserID=t.UserID,
            Username=t.Username,
            Amount=float(t.Amount),
            TransactionType=t.TransactionType,
            Status=t.Status,
            Description=t.Description,
            CreatedAt=t.CreatedAt,
            UpdatedAt=t.UpdatedAt,
            ReceiverID=t.ReceiverID,
            ReceiverUsername=t.ReceiverUsername,
        ).model_dump()
        for t in transactions
    ]

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={
            "items": [
                TransactionResponse(
                    TransactionID=t.TransactionID,
                    UserID=t.UserID,
                    Username=t.Username,
                    Amount=float(t.Amount),
                    TransactionType=t.TransactionType,
                    Status=t.Status,
                    Description=t.Description,
                    CreatedAt=t.CreatedAt,
                    UpdatedAt=t.UpdatedAt,
                    ReceiverID=t.ReceiverID,
                    ReceiverUsername=t.ReceiverUsername,
                ).model_dump()
                for t in transactions
            ]
        },
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=(total_items + per_page - 1) // per_page,
    )
