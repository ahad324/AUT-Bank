# app/routes/atm.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.withdrawal_schema import WithdrawalCreate
from app.controllers.withdrawals.atm import create_withdrawal
from app.core.schemas import BaseResponse
from app.core.rate_limiter import limiter
import os

router = APIRouter()


@router.post("/withdrawals", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
def create_withdrawal_route(
    request: Request,
    withdrawal: WithdrawalCreate,
    db: Session = Depends(get_db),
):
    return create_withdrawal(withdrawal, db)
