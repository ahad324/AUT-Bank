from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.admin import Admin
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from app.core.exceptions import CustomHTTPException
from app.core.responses import success_response, error_response
import os
import uuid

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in the .env file")

user_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")
admin_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/admins/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "role_id": data.get("role_id")})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4()), "role_id": data.get("role_id")})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(user_oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = CustomHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message="Could not validate credentials",
        details={}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.UserID == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user

def get_current_admin(token: str = Depends(admin_oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = CustomHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        message="Could not validate credentials",
        details={}
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id: str = payload.get("sub")
        role_id: int = payload.get("role_id")
        if admin_id is None or role_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    admin = db.query(Admin).filter(Admin.AdminID == int(admin_id)).first()
    if admin is None or admin.RoleID != role_id:
        raise credentials_exception
    return admin

def refresh_token(refresh_token: str, db: Session, model, role: str, id_field: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        entity_id: str = payload.get("sub")
        role_id: int = payload.get("role_id")
        if entity_id is None or role_id is None:
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid refresh token",
                details={}
            )
        
        entity = db.query(model).filter(getattr(model, id_field) == int(entity_id)).first()
        if not entity:
            raise CustomHTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message=f"{role} not found",
                details={}
            )
        
        new_access_token = create_access_token(data={"sub": str(entity_id), "role_id": role_id})
        new_refresh_token = create_refresh_token(data={"sub": str(entity_id), "role_id": role_id})
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