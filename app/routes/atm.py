# app/routes/atm.py
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.withdrawal_schema import WithdrawalCreate
from app.controllers.withdrawals.atm import create_withdrawal
from app.core.schemas import BaseResponse
from app.core.rate_limiter import limiter
import os

router = APIRouter()


@router.post("/withdraw", response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_USER_DEFAULT", "100/hour"))
async def create_withdrawal_route(
    request: Request,
    withdrawal: WithdrawalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    return await create_withdrawal(withdrawal, db, background_tasks)
