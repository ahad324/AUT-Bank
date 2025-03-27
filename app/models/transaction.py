from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "Transactions"

    TransactionID = Column(Integer, primary_key=True, index=True)
    SenderID = Column(Integer, ForeignKey("Users.UserID", ondelete="NO ACTION"), nullable=True)
    ReceiverID = Column(Integer, ForeignKey("Users.UserID", ondelete="NO ACTION"), nullable=True)
    Amount = Column(DECIMAL(19,4), nullable=False)
    TransactionType = Column(SQLEnum("Deposit", "Withdrawal", "Transfer", "Loan Repayment", name="transaction_type"), nullable=False)
    Status = Column(SQLEnum("Pending", "Completed", "Failed", name="transaction_status"), server_default="Pending")
    ReferenceNumber = Column(String(50), nullable=True)
    Description = Column(String(255), nullable=True)
    Timestamp = Column(DateTime, server_default=func.now())