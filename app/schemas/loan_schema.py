from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional

class LoanApply(BaseModel):
    LoanTypeID: int
    LoanAmount: Decimal
    LoanDurationMonths: int
    DueDate: date

class LoanPaymentCreate(BaseModel):
    LoanID: int
    PaymentAmount: Decimal

class LoanResponse(BaseModel):
    LoanID: int
    LoanTypeName: str
    LoanAmount: Decimal
    InterestRate: Decimal
    LoanDurationMonths: int
    MonthlyInstallment: Decimal
    DueDate: date
    LoanStatus: str
    CreatedAt: Optional[date]

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class LoanPaymentResponse(BaseModel):
    PaymentID: int
    LoanID: int
    PaymentAmount: Decimal
    PaymentDate: date
    LateFee: Decimal
    TotalAmountPaid: Decimal

    class Config:
        from_attributes = True 