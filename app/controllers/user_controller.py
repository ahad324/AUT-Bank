from fastapi import Depends, status
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException, DatabaseError
from app.schemas.user_schema import UserCreate, UserLogin, UserPasswordUpdate, UserResponseData, LoginResponseData, UserUpdate
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
        new_user.Password = pwd_context.hash(user.Password)
        
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
    
    if not user or not pwd_context.verify(credentials.Password, user.Password):
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
    
    access_token = create_access_token(data={"sub": str(user.UserID), "role_id": 0})
    refresh_token = create_refresh_token(data={"sub": str(user.UserID), "role_id": 0})
    return success_response(
        message="Login successful",
        data={
            **LoginResponseData.model_validate(user).model_dump(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    )

def update_current_user(user_id: int, user_update: UserUpdate, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

    # Prevent users from updating sensitive fields
    restricted_fields = {"IsActive", "Balance", "Password", "AccountType"}
    if any(field in restricted_fields for field in user_update.model_dump(exclude_unset=True).keys()):
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Cannot update restricted fields (e.g., IsActive, Balance, Password) via this endpoint. Use /me/password for password changes."
        )

    # Check for unique constraints
    if user_update.Username and user_update.Username != user.Username:
        if db.query(User).filter(User.Username == user_update.Username).first():
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Username already exists")
    if user_update.Email and user_update.Email != user.Email:
        if db.query(User).filter(User.Email == user_update.Email).first():
            raise CustomHTTPException(status_code=status.HTTP_400_BAD_REQUEST, message="Email already exists")

    # Apply updates
    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    try:
        db.commit()
        db.refresh(user)
        return success_response(
            message="Profile updated successfully",
            data=UserResponseData.model_validate(user).model_dump()
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update profile",
            details={"error": str(e)}
        )    
        
def update_user_password(user_id: int, password_update: UserPasswordUpdate, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

    # Verify current password
    if not pwd_context.verify(password_update.CurrentPassword, user.Password):
        raise CustomHTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Current password is incorrect"
        )

    # Update password
    user.Password = pwd_context.hash(password_update.NewPassword)

    try:
        db.commit()
        db.refresh(user)        
        return success_response(
            message="Password updated successfully",
            data={"UserID": user.UserID}
        )
    except Exception as e:
        db.rollback()
        raise CustomHTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update password",
            details={"error": str(e)}
        )