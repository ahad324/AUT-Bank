from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
# Controller
from app.controllers.user_controller import register_user, login_user
from app.controllers.transaction_controller import create_transaction
# Schemas
from app.schemas.user_schema import UserCreate, UserLogin
from app.schemas.transaction_schema import TransactionCreate
# Models
from app.models.user import User
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse
from app.core.auth import get_current_user, refresh_token

router = APIRouter()

@router.post("/register", response_model=BaseResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login", response_model=BaseResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    return login_user(credentials, db)

@router.post("/transactions", response_model=BaseResponse)
def perform_transaction(
    transaction: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return create_transaction(current_user.UserID, transaction, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh(token: str, db: Session = Depends(get_db)):
    return refresh_token(token, db, User, "User", "UserID")