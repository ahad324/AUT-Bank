from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from app.models.loan import Loan, LoanType, LoanPayment
from app.models.user import User
from app.schemas.loan_schema import LoanApply, LoanPaymentCreate, LoanResponse, LoanPaymentResponse
from app.core.responses import success_response
from app.core.schemas import BaseResponse, PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional

def apply_loan(user_id: int, loan: LoanApply, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

    loan_type = db.query(LoanType).filter(LoanType.LoanTypeID == loan.LoanTypeID).first()
    if not loan_type:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Loan type not found")

    if loan.LoanAmount <= 0 or loan.LoanDurationMonths <= 0:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid loan amount or duration")

    new_loan = Loan(
        UserID=user_id,
        LoanTypeID=loan.LoanTypeID,
        LoanAmount=loan.LoanAmount,
        InterestRate=loan_type.DefaultInterestRate,
        LoanDurationMonths=loan.LoanDurationMonths,
        DueDate=loan.DueDate,
        LoanStatus="Pending"
    )
    try:
        db.add(new_loan)
        db.commit()
        db.refresh(new_loan)
        return success_response(
            message="Loan application submitted successfully",
            data={"LoanID": new_loan.LoanID, "MonthlyInstallment": float(new_loan.MonthlyInstallment)}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=f"Failed to apply loan: {str(e)}")

def get_loan_types(db: Session):
    loan_types = db.query(LoanType).all()
    return success_response(
        message="Loan types retrieved successfully",
        data={"loan_types": [{
            "LoanTypeID": lt.LoanTypeID,
            "LoanTypeName": lt.LoanTypeName,
            "DefaultInterestRate": float(lt.DefaultInterestRate),
            "LatePaymentFeePerDay": float(lt.LatePaymentFeePerDay)
        } for lt in loan_types]}
    )

def make_loan_payment(user_id: int, payment: LoanPaymentCreate, db: Session):
    loan = db.query(Loan).filter(Loan.LoanID == payment.LoanID, Loan.UserID == user_id).first()
    if not loan:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Loan not found or not owned by user")
    
    if loan.LoanStatus != "Approved":
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Loan must be approved to accept payments")
    
    if payment.PaymentAmount <= 0:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Payment amount must be positive")

    loan_type = db.query(LoanType).filter(LoanType.LoanTypeID == loan.LoanTypeID).first()
    if not loan_type:
        raise CustomHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="Loan type not found")

    payment_date = payment.PaymentDate if payment.PaymentDate else date.today()
    late_days = max(0, (payment_date - loan.DueDate).days) if payment_date > loan.DueDate else 0
    late_fee = late_days * float(loan_type.LatePaymentFeePerDay)

    new_payment = LoanPayment(
        LoanID=payment.LoanID,
        PaymentAmount=payment.PaymentAmount,
        PaymentDate=payment_date,
        LateFee=late_fee
    )
    
    try:
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
        
        total_paid = db.query(func.sum(LoanPayment.TotalAmountPaid)).filter(LoanPayment.LoanID == payment.LoanID).scalar() or 0
        total_due = loan.LoanAmount + (loan.MonthlyInstallment * loan.LoanDurationMonths - loan.LoanAmount)
        if total_paid >= total_due:
            loan.LoanStatus = "Repaid"
            db.commit()
        
        return success_response(
            message="Payment recorded successfully",
            data={"PaymentID": new_payment.PaymentID, "LateFee": float(new_payment.LateFee)}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=f"Failed to record payment: {str(e)}")

def get_user_loans(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    status: Optional[str] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc"
):
    query = (
        db.query(Loan, LoanType.LoanTypeName)
        .join(LoanType, Loan.LoanTypeID == LoanType.LoanTypeID)
        .filter(Loan.UserID == user_id)
    )

    if status:
        if status not in ["Pending", "Approved", "Rejected", "Repaid"]:
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status value")
        query = query.filter(Loan.LoanStatus == status)

    total_loans = query.count()

    sort_column = {
        "CreatedAt": Loan.CreatedAt,
        "DueDate": Loan.DueDate,
        "LoanAmount": Loan.LoanAmount,
        "MonthlyInstallment": Loan.MonthlyInstallment
    }.get(sort_by, Loan.CreatedAt)
    order_func = desc if order.lower() == "desc" else asc
    query = query.order_by(order_func(sort_column))

    offset = (page - 1) * per_page
    loans = query.offset(offset).limit(per_page).all()
    
    if not loans:
        paginated_response = PaginatedResponse(
            success=True,
            message="No loans found for this user",
            data={"loans": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
        ).model_dump()
        return success_response(
            message=paginated_response["message"],
            data=paginated_response
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
            CreatedAt=loan.CreatedAt.date() if loan.CreatedAt else None
        )
        for loan, loan_type_name in loans
    ]
    
    total_pages = (total_loans + per_page - 1) // per_page
    
    paginated_response = PaginatedResponse(
        success=True,
        message="Loans retrieved successfully",
        data={"loans": [loan.model_dump() for loan in loan_list]},
        page=page,
        per_page=per_page,
        total_items=total_loans,
        total_pages=total_pages
    ).model_dump()
    
    return success_response(
        message=paginated_response["message"],
        data=paginated_response
    )

def get_loan_payments(user_id: int, loan_id: int, db: Session, page: int = 1, per_page: int = 10):
    loan = db.query(Loan).filter(Loan.LoanID == loan_id, Loan.UserID == user_id).first()
    if not loan:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Loan not found or not owned by user")

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
        paginated_response = PaginatedResponse(
            success=True,
            message="No payments found for this loan",
            data={"payments": []},
            page=page,
            per_page=per_page,
            total_items=total_payments,
            total_pages=0 if total_payments == 0 else (total_payments + per_page - 1) // per_page
        ).model_dump()
        return success_response(
            message=paginated_response["message"],
            data=paginated_response
        )
    
    payment_list = [LoanPaymentResponse.from_orm(payment) for payment in payments]
    
    paginated_response = PaginatedResponse(
        success=True,
        message="Payments retrieved successfully",
        data={"payments": [payment.model_dump() for payment in payment_list]},
        page=page,
        per_page=per_page,
        total_items=total_payments,
        total_pages=(total_payments + per_page - 1) // per_page
    ).model_dump()
    
    return success_response(
        message=paginated_response["message"],
        data=paginated_response
    )