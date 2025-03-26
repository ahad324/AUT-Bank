from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.sql import func, text
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "Transactions"

    TransactionID = Column(Integer, primary_key=True, index=True)
    SenderID = Column(Integer, ForeignKey("Users.UserID", ondelete="NO ACTION"), nullable=True)
    ReceiverID = Column(Integer, ForeignKey("Users.UserID", ondelete="NO ACTION"), nullable=True)
    Amount = Column(DECIMAL(19,4), nullable=False)
    TransactionType = Column(String(20), nullable=False)
    ReferenceNumber = Column(String(50), nullable=True)
    Status = Column(String(20), server_default='Pending')
    Description = Column(String(255), nullable=True)
    Timestamp = Column(DateTime, server_default=func.now())