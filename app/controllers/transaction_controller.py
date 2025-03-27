from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction_schema import DepositRequest, TransactionCreate, TransactionResponse
from app.core.responses import success_response
from app.core.exceptions import CustomHTTPException
from fastapi import status
import uuid
from decimal import Decimal

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

def deposit(user_id: int, deposit: DepositRequest, db: Session):
    # Verify user exists
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            details={}
        )

    # Convert deposit.Amount to Decimal
    amount = Decimal(str(deposit.Amount))
    
    # Create a deposit transaction
    deposit_transaction = Transaction(
        SenderID=None,  # No sender for a deposit
        ReceiverID=user_id,  # The user receiving the deposit
        Amount=amount,
        TransactionType="Deposit",
        ReferenceNumber=str(uuid.uuid4()),
        Status="Pending",
        Description=deposit.Description
    )

    try:
        # Update user's balance
        user.Balance += amount
        deposit_transaction.Status = "Completed"
        db.add(deposit_transaction)
        db.commit()
        db.refresh(deposit_transaction)

        return success_response(
            message="Deposit completed successfully",
            data=TransactionResponse.model_validate(deposit_transaction).model_dump()
        )
    except Exception as e:
        db.rollback()
        deposit_transaction.Status = "Failed"
        db.commit()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Deposit failed",
            details={"error": str(e)}
        )
        
def get_all_transactions(page: int, per_page: int, db: Session):
    offset = (page - 1) * per_page
    transactions = db.query(Transaction).order_by(Transaction.Timestamp.desc()).offset(offset).limit(per_page).all()
    total_items = db.query(Transaction).count()
    total_pages = (total_items + per_page - 1) // per_page

    return success_response(
        message="Transactions retrieved successfully",
        data={
            "transactions": [TransactionResponse.model_validate(t).model_dump() for t in transactions],
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": total_pages
        }
    )