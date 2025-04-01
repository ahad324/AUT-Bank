from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.withdrawal_schema import WithdrawalCreate
from app.controllers.withdrawals.atm import create_withdrawal
from app.core.schemas import BaseResponse

router = APIRouter()

@router.post("/withdrawals", response_model=BaseResponse)
def create_withdrawal_route(
    withdrawal: WithdrawalCreate,
    db: Session = Depends(get_db)
):
    return create_withdrawal(withdrawal, db)