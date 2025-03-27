from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.admin import Admin
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.core.exceptions import CustomHTTPException
from app.core.responses import success_response, error_response
import os
import uuid

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})  # Unique identifier for refresh token
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = CustomHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message="Could not validate credentials",
        details={}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role not in ["User", "Admin"]:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if role == "User":
        user = db.query(User).filter(User.UserID == user_id).first()
        if user is None:
            raise credentials_exception
        return user
    elif role == "Admin":
        admin = db.query(Admin).filter(Admin.AdminID == user_id).first()
        if admin is None:
            raise credentials_exception
        return admin

def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    if not isinstance(user, Admin):
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Admin access required",
            details={}
        )
    return user

def refresh_token(refresh_token: str, db: Session, model, role: str, id_field: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        entity_id: int = int(payload.get("sub"))
        token_role: str = payload.get("role")
        if entity_id is None or token_role != role:
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token",
                details={}
            )
        
        entity = db.query(model).filter(getattr(model, id_field) == entity_id).first()
        if not entity:
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=f"{role} not found",
                details={}
            )
        
        new_access_token = create_access_token(data={"sub": str(entity_id), "role": role})
        new_refresh_token = create_refresh_token(data={"sub": str(entity_id), "role": role})
        return success_response(
            message="Token refreshed successfully",
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
        )
    except JWTError:
        return error_response(
            message="Invalid or expired refresh token",
            status_code=status.HTTP_401_UNAUTHORIZED
        )