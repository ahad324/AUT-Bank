from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from app.models.loan import Loan, LoanType, LoanPayment
from app.models.user import User
from app.schemas.loan_schema import (
    LoanApply,
    LoanPaymentCreate,
    LoanResponse,
    LoanPaymentResponse,
)
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional
from dateutil.relativedelta import relativedelta


def apply_loan(user_id: int, loan: LoanApply, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )
    if not user.IsActive:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Inactive users cannot apply for loans",
        )

    loan_type = (
        db.query(LoanType).filter(LoanType.LoanTypeID == loan.LoanTypeID).first()
    )
    if not loan_type:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="Loan type not found"
        )

    if loan.LoanAmount <= 0 or loan.LoanDurationMonths <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid loan amount or duration",
        )

    new_loan = Loan(
        UserID=user_id,
        LoanTypeID=loan.LoanTypeID,
        LoanAmount=loan.LoanAmount,
        InterestRate=loan_type.DefaultInterestRate,
        LoanDurationMonths=loan.LoanDurationMonths,
        DueDate=loan.DueDate,
        LoanStatus="Pending",
    )
    try:
        db.add(new_loan)
        db.commit()
        db.refresh(new_loan)
        return success_response(
            message="Loan application submitted successfully",
            data={
                "LoanID": new_loan.LoanID,
                "MonthlyInstallment": float(new_loan.MonthlyInstallment),
            },
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to apply loan: {str(e)}",
        )


def make_loan_payment(user_id: int, payment: LoanPaymentCreate, db: Session):
    # Fetch the loan and validate ownership
    loan = (
        db.query(Loan)
        .filter(Loan.LoanID == payment.LoanID, Loan.UserID == user_id)
        .first()
    )
    if not loan:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Loan not found or not owned by user",
        )

    if loan.LoanStatus != "Active":
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Loan must be active to accept payments",
        )

    if payment.PaymentAmount <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Payment amount must be positive",
        )

    # Fetch the user to check balance
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND, message="User not found"
        )

    if not user.IsActive:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Inactive users cannot make loan payments",
        )

    # Fetch loan type for late fee calculation
    loan_type = (
        db.query(LoanType).filter(LoanType.LoanTypeID == loan.LoanTypeID).first()
    )
    if not loan_type:
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Loan type not found",
        )

    # Calculate late fee based on overdue days
    payment_date = date.today()
    late_days = (
        max(0, (payment_date - loan.DueDate).days) if payment_date > loan.DueDate else 0
    )
    late_fee = Decimal(str(late_days)) * Decimal(str(loan_type.LatePaymentFeePerDay))

    # Calculate total due (principal + interest) and total paid so far
    total_due = Decimal(str(loan.LoanAmount)) + (
        Decimal(str(loan.MonthlyInstallment)) * Decimal(str(loan.LoanDurationMonths))
        - Decimal(str(loan.LoanAmount))
    )
    total_paid = db.query(func.sum(LoanPayment.PaymentAmount)).filter(
        LoanPayment.LoanID == payment.LoanID
    ).scalar() or Decimal("0")

    # Include any previous late fees in the total due
    total_late_fees_paid = db.query(func.sum(LoanPayment.LateFee)).filter(
        LoanPayment.LoanID == payment.LoanID
    ).scalar() or Decimal("0")
    total_due_with_late_fees = total_due + total_late_fees_paid + late_fee

    # Calculate remaining balance
    remaining_balance = total_due_with_late_fees - total_paid
    if remaining_balance <= 0:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Loan is already fully paid",
        )

    # Adjust payment amount to include late fee and cap at remaining balance
    total_payment_required = Decimal(str(payment.PaymentAmount)) + late_fee
    if user.Balance < total_payment_required:
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"Insufficient balance. Available: {float(user.Balance)}, Required: {float(total_payment_required)} (including late fee of {float(late_fee)})",
        )

    adjusted_payment_amount = min(
        Decimal(str(payment.PaymentAmount)), remaining_balance - late_fee
    )
    total_amount_deducted = adjusted_payment_amount + late_fee

    # Create the payment record
    new_payment = LoanPayment(
        LoanID=payment.LoanID,
        PaymentAmount=adjusted_payment_amount,
        PaymentDate=payment_date,
        LateFee=float(late_fee),  # Store as float for consistency
    )

    try:
        # Deduct the total amount (payment + late fee) from user balance
        user.Balance -= total_amount_deducted

        # Add payment and update loan
        db.add(new_payment)

        # Shift the due date forward by one month
        loan.DueDate = loan.DueDate + relativedelta(months=1)

        db.commit()
        db.refresh(new_payment)
        db.refresh(user)
        db.refresh(loan)

        # Check if loan is fully repaid
        total_paid = db.query(func.sum(LoanPayment.PaymentAmount)).filter(
            LoanPayment.LoanID == payment.LoanID
        ).scalar() or Decimal("0")
        total_late_fees_paid = db.query(func.sum(LoanPayment.LateFee)).filter(
            LoanPayment.LoanID == payment.LoanID
        ).scalar() or Decimal("0")
        if (total_paid + total_late_fees_paid) >= total_due_with_late_fees:
            loan.LoanStatus = "Repaid"
            db.commit()

        # Prepare response data
        response_data = {
            "PaymentID": new_payment.PaymentID,
            "PaymentAmount": float(new_payment.PaymentAmount),
            "LateFee": float(new_payment.LateFee),
            "TotalAmountDeducted": float(total_amount_deducted),
            "NewDueDate": loan.DueDate,
            "RemainingBalance": float(remaining_balance - total_amount_deducted),
            "LoanStatus": loan.LoanStatus,
        }
        if adjusted_payment_amount < Decimal(str(payment.PaymentAmount)):
            response_data["AdjustmentMessage"] = (
                f"Payment adjusted to {float(adjusted_payment_amount)} to avoid overpayment."
            )

        return success_response(
            message="Payment recorded successfully",
            data=response_data,
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to record payment: {str(e)}",
        )


def get_loan_types(db: Session):
    loan_types = db.query(LoanType).all()
    return success_response(
        message="Loan types retrieved successfully",
        data={
            "items": [
                {
                    "LoanTypeID": lt.LoanTypeID,
                    "LoanTypeName": lt.LoanTypeName,
                    "DefaultInterestRate": float(lt.DefaultInterestRate),
                    "LatePaymentFeePerDay": float(lt.LatePaymentFeePerDay),
                }
                for lt in loan_types
            ]
        },
    )


def get_user_loans(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    status: Optional[str] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc",
):
    query = (
        db.query(Loan, LoanType.LoanTypeName)
        .join(LoanType, Loan.LoanTypeID == LoanType.LoanTypeID)
        .filter(Loan.UserID == user_id)
    )

    if status:
        if status not in ["Pending", "Approved", "Rejected", "Repaid"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status value"
            )
        query = query.filter(Loan.LoanStatus == status)

    total_loans = query.count()

    sort_column = {
        "CreatedAt": Loan.CreatedAt,
        "DueDate": Loan.DueDate,
        "LoanAmount": Loan.LoanAmount,
        "MonthlyInstallment": Loan.MonthlyInstallment,
    }.get(sort_by, Loan.CreatedAt)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    offset = (page - 1) * per_page
    loans = query.offset(offset).limit(per_page).all()

    if not loans:
        return PaginatedResponse(
            success=True,
            message="No loans found for this user",
            data={"items": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0,
        )

    loan_list = [
        LoanResponse(
            LoanID=loan.LoanID,
            LoanTypeName=loan_type_name,
            LoanAmount=loan.LoanAmount,
            InterestRate=loan.InterestRate,
            LoanDurationMonths=loan.LoanDurationMonths,
            MonthlyInstallment=loan.MonthlyInstallment,
            DueDate=loan.DueDate,
            LoanStatus=loan.LoanStatus,
            CreatedAt=loan.CreatedAt.date() if loan.CreatedAt else None,
        )
        for loan, loan_type_name in loans
    ]

    total_pages = (total_loans + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Loans retrieved successfully",
        data={"items": [loan.model_dump() for loan in loan_list]},
        page=page,
        per_page=per_page,
        total_items=total_loans,
        total_pages=total_pages,
    )


def get_loan_payments(
    user_id: int, loan_id: int, db: Session, page: int = 1, per_page: int = 10
):
    loan = db.query(Loan).filter(Loan.LoanID == loan_id, Loan.UserID == user_id).first()
    if not loan:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Loan not found or not owned by user",
        )

    total_payments = db.query(LoanPayment).filter(LoanPayment.LoanID == loan_id).count()

    offset = (page - 1) * per_page
    payments = (
        db.query(LoanPayment)
        .filter(LoanPayment.LoanID == loan_id)
        .order_by(LoanPayment.PaymentDate.desc())
        .offset(offset)
        .limit(per_page)
        .all()
    )

    if not payments:
        return PaginatedResponse(
            success=True,
            message="No payments found for this loan",
            data={"items": []},
            page=page,
            per_page=per_page,
            total_items=total_payments,
            total_pages=(
                0
                if total_payments == 0
                else (total_payments + per_page - 1) // per_page
            ),
        )

    payment_list = [LoanPaymentResponse.model_validate(payment) for payment in payments]

    return PaginatedResponse(
        success=True,
        message="Payments retrieved successfully",
        data={"items": [payment.model_dump() for payment in payment_list]},
        page=page,
        per_page=per_page,
        total_items=total_payments,
        total_pages=(total_payments + per_page - 1) // per_page,
    )
