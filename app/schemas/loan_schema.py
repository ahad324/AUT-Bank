from pydantic import BaseModel, ConfigDict, Field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class LoanApply(BaseModel):
    LoanTypeID: int
    LoanAmount: Decimal = Field(gt=0)
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
    CreatedAt: Optional[datetime]
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        },
    )


class LoanPaymentResponse(BaseModel):
    PaymentID: int
    LoanID: int
    PaymentAmount: Decimal
    PaymentDate: date
    LateFee: Decimal
    TotalAmountPaid: Decimal
    model_config = ConfigDict(from_attributes=True)
