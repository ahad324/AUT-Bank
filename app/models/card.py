from sqlalchemy import Column, DateTime, Integer, String, Date, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Card(Base):
    __tablename__ = "Cards"

    CardID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID", ondelete="CASCADE"), nullable=False)
    CardNumber = Column(String(16), unique=True, nullable=False)
    Pin = Column(String(255), nullable=False)
    ExpirationDate = Column(Date, nullable=False)
    Status = Column(String(20), nullable=False, default="Active")
    CreatedAt = Column(DateTime, server_default=func.now())