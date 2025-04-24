from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Transfer(Base):
    __tablename__ = "Transfers"

    TransferID = Column(Integer, primary_key=True, index=True)
    SenderID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    ReceiverID = Column(Integer, ForeignKey("Users.UserID"), nullable=False)
    Amount = Column(DECIMAL(19, 4), nullable=False)
    ReferenceNumber = Column(String(50), nullable=False)
    Status = Column(String(20), nullable=False, default="Pending")
    Description = Column(String(255), nullable=True)
    CreatedAt = Column(DateTime, server_default=func.now())
