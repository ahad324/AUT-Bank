from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.schemas import BaseResponse
from app.schemas.user_schema import UserCreate, UserLogin, UserResponseData, LoginResponseData
from app.models.user import User
from app.core.database import get_db
from app.core.responses import success_response, error_response
from app.core.auth import create_access_token, create_refresh_token
from passlib.context import CryptContext
from datetime import datetime, timezone

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=BaseResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.Email == user.Email) | 
        (User.CNIC == user.CNIC) | 
        (User.Username == user.Username)
    ).first()

    if existing_user:
        field = "email" if existing_user.Email == user.Email else "CNIC" if existing_user.CNIC == user.CNIC else "username"
        return error_response(
            message=f"{field.capitalize()} already registered",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        new_user = User(**user.model_dump(exclude={"Password"}))
        new_user.PasswordHash = pwd_context.hash(user.Password)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return success_response(
            message="User registered successfully",
            data=UserResponseData.model_validate(new_user).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        return error_response(
            message="Registration failed",
            details={"error": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@router.post("/login", response_model=BaseResponse)
@router.post("/login", response_model=BaseResponse)
def login_user(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.Email == credentials.login_id) | 
        (User.Username == credentials.login_id)
    ).first()
    
    if not user or not pwd_context.verify(credentials.Password, user.PasswordHash):
        return error_response(
            message="Invalid credentials",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    user.LastLogin = datetime.now(timezone.utc)
    db.commit()
    
    access_token = create_access_token(data={"sub": str(user.UserID), "role": "User"})
    refresh_token = create_refresh_token(data={"sub": str(user.UserID), "role": "User"})
    return success_response(
        message="Login successful",
        data={
            **LoginResponseData.model_validate(user).model_dump(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    )