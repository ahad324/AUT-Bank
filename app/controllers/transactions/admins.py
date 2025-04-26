import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc, union_all, literal
from app.core.responses import success_response
from app.models.transfer import Transfer
from app.models.deposit import Deposit
from app.models.withdrawal import Withdrawal
from app.schemas.transfer_schema import TransferResponse
from app.schemas.transactions_schema import TransactionResponse
from app.schemas.deposit_schema import DepositResponse
from app.schemas.withdrawal_schema import WithdrawalResponse
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date, datetime
from typing import Optional


from sqlalchemy import func, case, or_
from sqlalchemy.orm import Session, aliased
from app.models.user import User
from app.models.deposit import Deposit
from app.models.transfer import Transfer
from app.models.withdrawal import Withdrawal
from app.core.schemas import PaginatedResponse


def get_transaction_by_id(
    transaction_id: int, transaction_type: Optional[str], db: Session
):
    if transaction_type and transaction_type not in [
        "Deposit",
        "Transfer",
        "Withdrawal",
    ]:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, message="Invalid transaction type"
        )

    if transaction_type:
        model = {"Deposit": Deposit, "Transfer": Transfer, "Withdrawal": Withdrawal}[
            transaction_type
        ]
        transaction = (
            db.query(model)
            .filter(model.__table__.c[f"{transaction_type}ID"] == transaction_id)
            .first()
        )
        if not transaction:
            raise CustomHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"{transaction_type} not found",
            )
        schema = {
            "Deposit": DepositResponse,
            "Transfer": TransferResponse,
            "Withdrawal": WithdrawalResponse,
        }[transaction_type]
        return success_response(
            message=f"{transaction_type} details retrieved successfully",
            data=schema.model_validate(transaction).model_dump(),
        )
    else:
        # Alias for User and Receiver
        UserAlias = aliased(User)
        Receiver = aliased(User)

        # Unified query for all transaction types
        query = (
            db.query(
                func.coalesce(
                    Deposit.DepositID, Transfer.TransferID, Withdrawal.WithdrawalID
                ).label("TransactionID"),
                UserAlias.UserID.label("UserID"),
                UserAlias.Username.label("Username"),
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
            .select_from(UserAlias)
            .outerjoin(Deposit, Deposit.UserID == UserAlias.UserID)
            .outerjoin(Transfer, Transfer.SenderID == UserAlias.UserID)
            .outerjoin(Withdrawal, Withdrawal.UserID == UserAlias.UserID)
            .outerjoin(Receiver, Receiver.UserID == Transfer.ReceiverID)
            .filter(
                or_(
                    Deposit.DepositID == transaction_id,
                    Transfer.TransferID == transaction_id,
                    Withdrawal.WithdrawalID == transaction_id,
                )
            )
        )

        transaction = query.first()
        if not transaction:
            raise CustomHTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                message="Transaction not found",
            )

        return success_response(
            message=f"{transaction.TransactionType} details retrieved successfully",
            data=TransactionResponse(
                TransactionID=transaction.TransactionID,
                UserID=transaction.UserID,
                Username=transaction.Username,
                Amount=float(transaction.Amount),
                TransactionType=transaction.TransactionType,
                Status=transaction.Status,
                Description=transaction.Description,
                CreatedAt=transaction.CreatedAt,
                UpdatedAt=transaction.UpdatedAt,
                ReceiverID=transaction.ReceiverID,
                ReceiverUsername=transaction.ReceiverUsername,
            ).model_dump(),
        )


# ... (other imports remain the same)
def export_transactions(
    db: Session,
    user_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    transaction_status: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    # Alias for User
    UserAlias = aliased(User)
    Receiver = aliased(User)

    # Base query
    query = (
        db.query(
            func.coalesce(
                Deposit.DepositID, Transfer.TransferID, Withdrawal.WithdrawalID
            ).label("TransactionID"),
            UserAlias.Username.label("Username"),
            func.coalesce(Deposit.Amount, Transfer.Amount, Withdrawal.Amount).label(
                "Amount"
            ),
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status).label(
                "Status"
            ),
            func.coalesce(
                Deposit.CreatedAt, Transfer.CreatedAt, Withdrawal.CreatedAt
            ).label("CreatedAt"),
            case(
                (Deposit.DepositID.isnot(None), "Deposit"),
                (Transfer.TransferID.isnot(None), "Transfer"),
                (Withdrawal.WithdrawalID.isnot(None), "Withdrawal"),
            ).label("TransactionType"),
            Transfer.ReceiverID.label("ReceiverID"),
        )
        .select_from(UserAlias)
        .outerjoin(Deposit, Deposit.UserID == UserAlias.UserID)
        .outerjoin(Transfer, Transfer.SenderID == UserAlias.UserID)
        .outerjoin(Withdrawal, Withdrawal.UserID == UserAlias.UserID)
        .outerjoin(Receiver, Receiver.UserID == Transfer.ReceiverID)
        .filter(
            or_(
                Deposit.DepositID.isnot(None),
                Transfer.TransferID.isnot(None),
                Withdrawal.WithdrawalID.isnot(None),
            )
        )
    )

    # Apply filters
    if user_id:
        query = query.filter(UserAlias.UserID == user_id)
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
    if transaction_status:
        if transaction_status not in ["Pending", "Completed", "Failed"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction status value",
            )
        query = query.filter(
            func.coalesce(Deposit.Status, Transfer.Status, Withdrawal.Status)
            == transaction_status
        )
    if transaction_type:
        if transaction_type not in ["Deposit", "Transfer", "Withdrawal"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid transaction type",
            )
        if transaction_type == "Deposit":
            query = query.filter(Deposit.DepositID.isnot(None))
        elif transaction_type == "Transfer":
            query = query.filter(Transfer.TransferID.isnot(None))
        elif transaction_type == "Withdrawal":
            query = query.filter(Withdrawal.WithdrawalID.isnot(None))

    # Execute query
    transactions = query.all()

    if not transactions:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No transactions found for export",
        )

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Write headers
    headers = [
        "TransactionID",
        "Username",
        "Amount",
        "Status",
        "CreatedAt",
        "TransactionType",
        "ReceiverUsername",
    ]
    writer.writerow(headers)

    # Fetch receiver usernames for transfers
    receiver_ids = {t.ReceiverID for t in transactions if t.ReceiverID}
    receivers = (
        db.query(User.UserID, User.Username).filter(User.UserID.in_(receiver_ids)).all()
    )
    receiver_map = {r.UserID: r.Username for r in receivers}

    # Write rows
    for t in transactions:
        receiver_username = receiver_map.get(t.ReceiverID, "") if t.ReceiverID else ""
        writer.writerow(
            [
                t.TransactionID,
                t.Username,
                f"{float(t.Amount):.2f}",
                t.Status,
                t.CreatedAt.strftime("%Y-%m-%d %H:%M:%S") if t.CreatedAt else "",
                t.TransactionType,
                receiver_username,
            ]
        )

    # Prepare streaming response
    output.seek(0)
    filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def get_all_transactions(
    db: Session,
    page: int = 1,
    per_page: int = 10,
    user_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    transaction_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc",
):
    # Validate or convert user_id to integer
    if user_id is not None:
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid user_id: must be an integer",
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
        .outerjoin(Transfer, Transfer.SenderID == User.UserID)
        .outerjoin(Withdrawal, Withdrawal.UserID == User.UserID)
        .outerjoin(Receiver, Receiver.UserID == Transfer.ReceiverID)
        .filter(
            or_(
                Deposit.DepositID.isnot(None),
                Transfer.TransferID.isnot(None),
                Withdrawal.WithdrawalID.isnot(None),
            )
        )
    )

    # Apply filters
    if user_id:
        query = query.filter(User.UserID == user_id)
    if transaction_type in ["Deposit", "Transfer", "Withdrawal"]:
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

    # Sorting with a fallback to ensure ORDER BY is always present
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
