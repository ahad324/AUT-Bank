from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Boolean,
    DECIMAL,
    Date,
)
from sqlalchemy.sql import func, text
from app.core.database import Base


class User(Base):
    __tablename__ = "Users"

    UserID = Column(Integer, primary_key=True, index=True)
    Username = Column(String(50), unique=True, nullable=False)
    FirstName = Column(String(50), nullable=False, server_default="")
    LastName = Column(String(50), nullable=False, server_default="")
    StreetAddress = Column(String(255), nullable=True)
    City = Column(String(50), nullable=True)
    State = Column(String(50), nullable=True)
    Country = Column(String(50), nullable=True)
    PostalCode = Column(String(20), nullable=True)
    PhoneNumber = Column(String(20), nullable=True)
    CNIC = Column(
        String(15),
        CheckConstraint(
            "CNIC LIKE '[0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9]'"
        ),
        unique=True,
        nullable=False,
    )
    Email = Column(String(100), unique=True, nullable=False)
    Password = Column(String(255), nullable=False)
    AccountType = Column(
        String(10),
        CheckConstraint("AccountType IN ('Savings', 'Current')"),
        nullable=False,
    )
    Balance = Column(DECIMAL(19, 4), server_default=text("0.0000"))
    DateOfBirth = Column(Date, nullable=False)
    IsActive = Column(Boolean, default=False)
    CreatedAt = Column(DateTime, server_default=func.now())
    LastLogin = Column(DateTime, nullable=True)
    ApprovedByAdminID = Column(Integer, ForeignKey("Admins.AdminID"), nullable=True)
