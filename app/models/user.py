from sqlalchemy import Column, Integer, String, DateTime, Boolean, DECIMAL
from sqlalchemy.sql import func
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, nullable=False)
    CNIC = Column(String(15), unique=True, nullable=False)
    Email = Column(String(100), unique=True, nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    AccountType = Column(String(10), nullable=False)
    Balance = Column(DECIMAL(18, 2), default=0)
    BiometricEnabled = Column(Boolean, default=False)
    DateOfBirth = Column(DateTime, nullable=False)  # ✅ Fix: Use DateTime instead of Date
    CreatedAt = Column(DateTime, default=func.now())
