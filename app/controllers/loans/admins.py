from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc
from app.models.loan import Loan, LoanType
from app.models.user import User
from app.models.admin import Admin
from app.schemas.loan_schema import LoanResponse
from app.core.responses import success_response
from app.core.schemas import PaginatedResponse
from app.core.exceptions import CustomHTTPException
from fastapi import status
from datetime import date
from typing import Optional

def approve_loan(loan_id: int, new_status: str, admin: Admin, db: Session):    
    loan = db.query(Loan).filter(Loan.LoanID == loan_id).first()
    if not loan:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="Loan not found")
    
    if new_status not in ["Approved", "Rejected"]:
        raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Invalid status")

    loan.LoanStatus = new_status
    try:
        db.commit()
        return success_response(message=f"Loan {new_status.lower()} successfully", data={"LoanID": loan.LoanID})
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=f"Failed to update loan: {str(e)}")

def get_all_loans(
    db: Session,
    page: int = 1,
    per_page: int = 10,
    loan_status: Optional[str] = None,
    user_id: Optional[int] = None,
    loan_type_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc"
):
    query = (
        db.query(Loan, LoanType.LoanTypeName)
        .join(LoanType, Loan.LoanTypeID == LoanType.LoanTypeID)
    )

    if loan_status:
        if loan_status not in ["Pending", "Approved", "Rejected", "Repaid"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid loan status"
            )
        query = query.filter(Loan.LoanStatus == loan_status)

    if user_id:
        query = query.filter(Loan.UserID == user_id)

    if loan_type_id:
        query = query.filter(Loan.LoanTypeID == loan_type_id)

    if start_date and end_date:
        if start_date > end_date:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="start_date must be before end_date"
            )
        query = query.filter(Loan.CreatedAt.between(start_date, end_date))
    elif start_date:
        query = query.filter(Loan.CreatedAt >= start_date)
    elif end_date:
        query = query.filter(Loan.CreatedAt <= end_date)

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
        return PaginatedResponse(
            success=True,
            message="No loans found",
            data={"loans": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
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

    return PaginatedResponse(
        success=True,
        message="Loans retrieved successfully",
        data={"loans": [loan.model_dump() for loan in loan_list]},
        page=page,
        per_page=per_page,
        total_items=total_loans,
        total_pages=total_pages
    )
    
def get_user_loans_for_admin(
    user_id: int,
    db: Session,
    page: int = 1,
    per_page: int = 10,
    loan_status: Optional[str] = None,
    loan_type_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort_by: Optional[str] = "CreatedAt",
    order: Optional[str] = "desc"
):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    query = (
        db.query(Loan, LoanType.LoanTypeName)
        .join(LoanType, Loan.LoanTypeID == LoanType.LoanTypeID)
        .filter(Loan.UserID == user_id)
    )

    if loan_status:
        if loan_status not in ["Pending", "Approved", "Rejected", "Repaid"]:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid loan status"
            )
        query = query.filter(Loan.LoanStatus == loan_status)

    if loan_type_id:
        query = query.filter(Loan.LoanTypeID == loan_type_id)

    if start_date and end_date:
        if start_date > end_date:
            raise CustomHTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="start_date must be before end_date"
            )
        query = query.filter(Loan.CreatedAt.between(start_date, end_date))
    elif start_date:
        query = query.filter(Loan.CreatedAt >= start_date)
    elif end_date:
        query = query.filter(Loan.CreatedAt <= end_date)

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
        return PaginatedResponse(
            success=True,
            message="No loans found for this user",
            data={"loans": []},
            page=page,
            per_page=per_page,
            total_items=0,
            total_pages=0
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

    return PaginatedResponse(
        success=True,
        message="Loans retrieved successfully",
        data={"loans": [loan.model_dump() for loan in loan_list]},
        page=page,
        per_page=per_page,
        total_items=total_loans,
        total_pages=total_pages
    )

def get_loan_by_id(loan_id: int, db: Session):
    result = (
        db.query(Loan, LoanType.LoanTypeName)
        .join(LoanType, Loan.LoanTypeID == LoanType.LoanTypeID)
        .filter(Loan.LoanID == loan_id)
        .first()
    )

    if not result:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Loan not found"
        )

    loan, loan_type_name = result
    loan_response = LoanResponse(
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

    return success_response(
        message="Loan retrieved successfully",
        data=loan_response.model_dump()
    )