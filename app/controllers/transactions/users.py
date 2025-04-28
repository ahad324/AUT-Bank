from sqlalchemy.orm import Session
from sqlalchemy import func, case, literal, or_, select, union
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

    # Subquery for Deposits
    deposit_query = (
        select(
            Deposit.DepositID.label("TransactionID"),
            Deposit.UserID.label("UserID"),
            User.Username.label("Username"),
            Deposit.Amount.label("Amount"),
            literal("Deposit").label("TransactionType"),
            Deposit.Status.label("Status"),
            Deposit.Description.label("Description"),
            Deposit.CreatedAt.label("CreatedAt"),
            Deposit.CreatedAt.label("UpdatedAt"),
            literal(None).label("ReceiverID"),
            literal(None).label("ReceiverUsername"),
        )
        .select_from(Deposit)
        .join(User, User.UserID == Deposit.UserID)
        .where(Deposit.UserID == user_id)
    )

    # Subquery for Transfers (both sent and received)
    transfer_query = (
        select(
            Transfer.TransferID.label("TransactionID"),
            Transfer.SenderID.label("UserID"),
            User.Username.label("Username"),
            Transfer.Amount.label("Amount"),
            literal("Transfer").label("TransactionType"),
            Transfer.Status.label("Status"),
            Transfer.Description.label("Description"),
            Transfer.CreatedAt.label("CreatedAt"),
            Transfer.CreatedAt.label("UpdatedAt"),
            Transfer.ReceiverID.label("ReceiverID"),
            Receiver.Username.label("ReceiverUsername"),
        )
        .select_from(Transfer)
        .join(User, User.UserID == Transfer.SenderID)
        .join(Receiver, Receiver.UserID == Transfer.ReceiverID)
        .where(or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id))
    )

    # Subquery for Withdrawals
    withdrawal_query = (
        select(
            Withdrawal.WithdrawalID.label("TransactionID"),
            Withdrawal.UserID.label("UserID"),
            User.Username.label("Username"),
            Withdrawal.Amount.label("Amount"),
            literal("Withdrawal").label("TransactionType"),
            Withdrawal.Status.label("Status"),
            Withdrawal.Description.label("Description"),
            Withdrawal.CreatedAt.label("CreatedAt"),
            Withdrawal.CreatedAt.label("UpdatedAt"),
            literal(None).label("ReceiverID"),
            literal(None).label("ReceiverUsername"),
        )
        .select_from(Withdrawal)
        .join(User, User.UserID == Withdrawal.UserID)
        .where(Withdrawal.UserID == user_id)
    )

    # Combine with union
    union_query = union(deposit_query, transfer_query, withdrawal_query).subquery()
    query = db.query(union_query)

    # Apply filters
    if transaction_type:
        query = query.filter(union_query.c.TransactionType == transaction_type)
    if transaction_status:
        query = query.filter(union_query.c.Status == transaction_status)
    if start_date:
        query = query.filter(union_query.c.CreatedAt >= start_date)
    if end_date:
        query = query.filter(union_query.c.CreatedAt <= end_date)

    # Sorting
    sort_field_map = {
        "TransactionID": union_query.c.TransactionID,
        "Amount": union_query.c.Amount,
        "CreatedAt": union_query.c.CreatedAt,
        "Status": union_query.c.Status,
    }
    sort_field = sort_field_map.get(sort_by, union_query.c.CreatedAt)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_field))

    # Pagination
    total_items = query.count()
    transactions = query.offset((page - 1) * per_page).limit(per_page).all()

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
