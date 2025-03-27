from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, ForeignKey, Date, Computed
from sqlalchemy.sql import func, text
from app.core.database import Base

class LoanType(Base):
    __tablename__ = "LoanTypes"

    LoanTypeID = Column(Integer, primary_key=True, index=True)
    LoanTypeName = Column(String(50), unique=True, nullable=False)
    DefaultInterestRate = Column(DECIMAL(5,2), nullable=False)
    LatePaymentFeePerDay = Column(DECIMAL(10,2), nullable=False)

class Loan(Base):
    __tablename__ = "Loans"

    LoanID = Column(Integer, primary_key=True, index=True)
    UserID = Column(Integer, ForeignKey("Users.UserID", ondelete="CASCADE"))
    LoanTypeID = Column(Integer, ForeignKey("LoanTypes.LoanTypeID", ondelete="CASCADE"))
    LoanAmount = Column(DECIMAL(19,4), nullable=False)
    InterestRate = Column(DECIMAL(5,2), nullable=False)
    LoanDurationMonths = Column(Integer, nullable=False)
    MonthlyInstallment = Column(
        DECIMAL(19,4), 
        Computed(
            "(LoanAmount * (InterestRate/100.0/12) * POWER(1 + (InterestRate/100.0/12), LoanDurationMonths)) / "
            "(POWER(1 + (InterestRate/100.0/12), LoanDurationMonths) - 1)"
        ),
        nullable=False
    )
    DueDate = Column(Date, nullable=False)
    LoanStatus = Column(String(20), server_default='Pending')
    CreatedAt = Column(DateTime, server_default=func.now())

class LoanPayment(Base):
    __tablename__ = "LoanPayments"

    PaymentID = Column(Integer, primary_key=True, index=True)
    LoanID = Column(Integer, ForeignKey("Loans.LoanID", ondelete="CASCADE"))
    PaymentAmount = Column(DECIMAL(19,4), nullable=False)
    PaymentDate = Column(Date, server_default=text("GETDATE()"))
    LateFee = Column(DECIMAL(10,2), server_default=text("0"))
    TotalAmountPaid = Column(
        DECIMAL(19,4),
        Computed("PaymentAmount + LateFee"),
        nullable=False
    )