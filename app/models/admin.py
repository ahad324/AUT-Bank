from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base

class Admin(Base):
    __tablename__ = "Admins"

    AdminID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    Email = Column(String(100), unique=True, nullable=False)
    Role = Column(String(20), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    LastLogin = Column(DateTime, nullable=True)