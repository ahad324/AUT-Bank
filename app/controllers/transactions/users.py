from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc, union_all, literal, select
from app.models.transfer import Transfer
from app.models.deposit import Deposit
from app.models.withdrawal import Withdrawal
from app.schemas.transfer_schema import TransferResponse
from app.schemas.deposit_schema import DepositResponse
from app.schemas.withdrawal_schema import WithdrawalResponse
from app.core.responses import success_response
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
    sort_by: Optional[str] = "Timestamp",
    order: Optional[str] = "desc",
):
    if transaction_type:
        if transaction_type not in ["Transfer", "Deposit", "Withdrawal"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type",
            )
        # Select the appropriate model based on transaction_type
        model = {"Transfer": Transfer, "Deposit": Deposit, "Withdrawal": Withdrawal}[
            transaction_type
        ]
        if transaction_type == "Transfer":
            query = db.query(Transfer).filter(
                or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id)
            )
        elif transaction_type == "Deposit":
            query = db.query(Deposit).filter(Deposit.UserID == user_id)
        elif transaction_type == "Withdrawal":
            query = db.query(Withdrawal).filter(Withdrawal.UserID == user_id)

        if transaction_status:
            if transaction_status not in ["Pending", "Completed", "Failed"]:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status"
                )
            query = query.filter_by(Status=transaction_status)

        if start_date and end_date:
            if start_date > end_date:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="start_date must be before end_date",
                )
            query = query.filter(
                model.Timestamp.between(start_date, end_date)
            )  # Use dynamic model
        elif start_date:
            query = query.filter(model.Timestamp >= start_date)
        elif end_date:
            query = query.filter(model.Timestamp <= end_date)

        total_items = query.count()
    else:
        transfer_query = (
            db.query(Transfer)
            .filter(or_(Transfer.SenderID == user_id, Transfer.ReceiverID == user_id))
            .add_columns(
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
        )
        deposit_query = (
            db.query(Deposit)
            .filter(Deposit.UserID == user_id)
            .add_columns(
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
        )
        withdrawal_query = (
            db.query(Withdrawal)
            .filter(Withdrawal.UserID == user_id)
            .add_columns(
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
        )
        union_query = union_all(transfer_query, deposit_query, withdrawal_query)

        # Wrap union_all in a subquery
        subquery = union_query.subquery()
        query = db.query(subquery)

        if transaction_status:
            if transaction_status not in ["Pending", "Completed", "Failed"]:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status"
                )
            query = query.filter(subquery.c.Status == transaction_status)

        if start_date and end_date:
            if start_date > end_date:
                raise CustomHTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message="start_date must be before end_date",
                )
            query = query.filter(subquery.c.Timestamp.between(start_date, end_date))
        elif start_date:
            query = query.filter(subquery.c.Timestamp >= start_date)
        elif end_date:
            query = query.filter(subquery.c.Timestamp <= end_date)

        total_items = query.count()

    sort_column = {"Timestamp": "Timestamp", "Amount": "Amount"}.get(
        sort_by, "Timestamp"
    )
    order_func = desc if order.lower() == "desc" else asc
    if transaction_type:
        # For single-table queries, use the correct model's columns
        sort_attr = getattr(model, sort_column)  # Use dynamic model
        query = query.order_by(order_func(sort_attr))
    else:
        # For union_all, use subquery column names
        query = query.order_by(order_func(subquery.c[sort_column]))

    offset = (page - 1) * per_page
    transactions = query.offset(offset).limit(per_page).all()

    if not transactions:
        return PaginatedResponse(
            success=True,
            message="No transactions found",
            data={"items": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0,
        )

    total_pages = (total_items + per_page - 1) // per_page

    transaction_list = []
    if transaction_type:
        # Single-table response
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
        # Union_all response
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
        data={"items": transaction_list},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
    )
