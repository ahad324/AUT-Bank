from fastapi import Depends, status
from sqlalchemy.orm import Session
from app.core.exceptions import DatabaseError
from app.schemas.user_schema import UserCreate, UserLogin, UserResponseData, LoginResponseData
from app.models.user import User
from app.core.database import get_db
from app.core.responses import success_response, error_response
from app.core.auth import create_access_token, create_refresh_token
from passlib.context import CryptContext
from datetime import datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(
        (User.Email == user.Email) | 
        (User.CNIC == user.CNIC) | 
        (User.Username == user.Username)
    ).first()

    if existing_user:
        field = "Email" if existing_user.Email == user.Email else "CNIC" if existing_user.CNIC == user.CNIC else "Username"
        return error_response(
            message=f"{field} already registered",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    try:
        new_user = User(**user.model_dump(exclude={"Password"}))
        new_user.PasswordHash = pwd_context.hash(user.Password)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return success_response(
            message="User registered successfully, pending admin approval",
            data=UserResponseData.model_validate(new_user).model_dump(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        raise DatabaseError(f"Database error: {str(e)}")

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
        
    if not user.IsActive:  # ✅ Prevent login if inactive
        return error_response(
            message="Account is pending approval",
            status_code=status.HTTP_403_FORBIDDEN
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
    