from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
# Controller
from app.controllers.user_controller import register_user, login_user
from app.controllers.transaction_controller import create_transaction, deposit
# Schemas
from app.core.responses import error_response, success_response
from app.schemas.user_schema import UserCreate, UserLogin
from app.schemas.transaction_schema import TransactionCreate, DepositRequest
# Models
from app.models.user import User
# Core
from app.core.database import get_db
from app.core.schemas import BaseResponse
from app.core.auth import ALGORITHM, SECRET_KEY, get_current_user, create_access_token
from app.core.exceptions import CustomHTTPException

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

@router.post("/deposit", response_model=BaseResponse)
def deposit_funds(
    deposit_request: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return deposit(current_user.UserID, deposit_request, db)

@router.post("/refresh", response_model=BaseResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role != "User":
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token",
                details={}
            )
        
        user = db.query(User).filter(User.UserID == user_id).first()
        if not user:
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="User not found",
                details={}
            )
        
        new_access_token = create_access_token(data={"sub": str(user.UserID), "role": "User"})
        return success_response(
            message="Token refreshed successfully",
            data={"access_token": new_access_token, "token_type": "bearer"}
        )
    except JWTError:
        return error_response(
            message="Invalid or expired refresh token",
            status_code=status.HTTP_401_UNAUTHORIZED
        )