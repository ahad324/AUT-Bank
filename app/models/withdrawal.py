from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Withdrawal(Base):
    __tablename__ = "Withdrawals"

    WithdrawalID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    CardID = Column(Integer, ForeignKey("Cards.CardID"), nullable=False)
    Amount = Column(DECIMAL(19, 4), nullable=False)
    ReferenceNumber = Column(String(50), nullable=False)
    Status = Column(String(20), nullable=False, default="Pending")
    Description = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
