from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc, union_all, literal
from app.models.transfer import Transfer
from app.models.deposit import Deposit
from app.models.withdrawal import Withdrawal
from app.schemas.transfer_schema import TransferResponse
from app.schemas.deposit_schema import DepositResponse
from app.schemas.withdrawal_schema import WithdrawalResponse
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
    transaction_status: Optional[
        str
    ] = None,  # Renamed to avoid conflict with fastapi.status
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "Timestamp",
    order: Optional[str] = "desc",
):
    if transaction_type:
        if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type",
            )
        model = {"Transfer": Transfer, "Deposit": Deposit, "Withdrawal": Withdrawal}[
            transaction_type
        ]
        query = db.query(model)
        if transaction_type == "Transfer" and user_id:
            query = query.filter(
                or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id)
            )
        elif user_id:
            query = query.filter(model.UserID == user_id)
    else:
        transfer_query = db.query(Transfer).add_columns(
            Transfer.TransferID.label("ID"),
            Transfer.SenderID.label("UserID"),
            Transfer.ReceiverID.label("RelatedUserID"),
            Transfer.Amount.label("Amount"),
            literal("Transfer").label("TransactionType"),
            Transfer.ReferenceNumber.label("ReferenceNumber"),
            Transfer.Status.label("Status"),
            Transfer.Description.label("Description"),
            Transfer.Timestamp.label("Timestamp"),
        )
        deposit_query = db.query(Deposit).add_columns(
            Deposit.DepositID.label("ID"),
            Deposit.UserID.label("UserID"),
            Deposit.AdminID.label("RelatedUserID"),
            Deposit.Amount.label("Amount"),
            literal("Deposit").label("TransactionType"),
            Deposit.ReferenceNumber.label("ReferenceNumber"),
            Deposit.Status.label("Status"),
            Deposit.Description.label("Description"),
            Deposit.Timestamp.label("Timestamp"),
        )
        withdrawal_query = db.query(Withdrawal).add_columns(
            Withdrawal.WithdrawalID.label("ID"),
            Withdrawal.UserID.label("UserID"),
            Withdrawal.CardID.label("RelatedUserID"),
            Withdrawal.Amount.label("Amount"),
            literal("Withdrawal").label("TransactionType"),
            Withdrawal.ReferenceNumber.label("ReferenceNumber"),
            Withdrawal.Status.label("Status"),
            Withdrawal.Description.label("Description"),
            Withdrawal.Timestamp.label("Timestamp"),
        )
        union_query = union_all(transfer_query, deposit_query, withdrawal_query)
        subquery = union_query.subquery()
        query = db.query(subquery)
        if user_id:
            query = query.filter(
                or_(subquery.c.UserID == user_id, subquery.c.RelatedUserID == user_id)
            )

    if transaction_status:
        if transaction_status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status"
            )
        if transaction_type:
            query = query.filter_by(Status=transaction_status)
        else:
            query = query.filter(subquery.c.Status == transaction_status)

    if start_date and end_date:
        if start_date > end_date:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="start_date must be before end_date",
            )
        if transaction_type:
            query = query.filter(model.Timestamp.between(start_date, end_date))
        else:
            query = query.filter(subquery.c.Timestamp.between(start_date, end_date))
    elif start_date:
        if transaction_type:
            query = query.filter(model.Timestamp >= start_date)
        else:
            query = query.filter(subquery.c.Timestamp >= start_date)
    elif end_date:
        if transaction_type:
            query = query.filter(model.Timestamp <= end_date)
        else:
            query = query.filter(subquery.c.Timestamp <= end_date)

    total_items = query.count()

    sort_column = {"Timestamp": "Timestamp", "Amount": "Amount"}.get(
        sort_by, "Timestamp"
    )
    order_func = desc if order.lower() == "desc" else asc
    if transaction_type:
        query = query.order_by(order_func(getattr(model, sort_column)))
    else:
        query = query.order_by(order_func(subquery.c[sort_column]))

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
            total_pages=0,
        )

    total_pages = (total_items + per_page - 1) // per_page

    transaction_list = []
    if transaction_type:
        if transaction_type == "Transfer":
            transaction_list = [
                TransferResponse.model_validate(t).model_dump() for t in transactions
            ]
        elif transaction_type == "Deposit":
            transaction_list = [
                DepositResponse.model_validate(t).model_dump() for t in transactions
            ]
        elif transaction_type == "Withdrawal":
            transaction_list = [
                WithdrawalResponse.model_validate(t).model_dump() for t in transactions
            ]
    else:
        for t in transactions:
            if t.TransactionType == "Transfer":
                transaction_list.append(
                    TransferResponse(
                        TransferID=t.ID,
                        SenderID=t.UserID,
                        ReceiverID=t.RelatedUserID,
                        Amount=float(t.Amount),
                        ReferenceNumber=t.ReferenceNumber,
                        Status=t.Status,
                        Description=t.Description,
                        Timestamp=t.Timestamp,
                    ).model_dump()
                )
            elif t.TransactionType == "Deposit":
                transaction_list.append(
                    DepositResponse(
                        DepositID=t.ID,
                        UserID=t.UserID,
                        AdminID=t.RelatedUserID,
                        Amount=float(t.Amount),
                        ReferenceNumber=t.ReferenceNumber,
                        Status=t.Status,
                        Description=t.Description,
                        Timestamp=t.Timestamp,
                    ).model_dump()
                )
            elif t.TransactionType == "Withdrawal":
                transaction_list.append(
                    WithdrawalResponse(
                        WithdrawalID=t.ID,
                        UserID=t.UserID,
                        CardID=t.RelatedUserID,
                        Amount=float(t.Amount),
                        ReferenceNumber=t.ReferenceNumber,
                        Status=t.Status,
                        Description=t.Description,
                        Timestamp=t.Timestamp,
                    ).model_dump()
                )

    return PaginatedResponse(
        success=True,
        message="Transactions retrieved successfully",
        data={"transactions": transaction_list},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    )
