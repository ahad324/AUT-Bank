from typing import Optional
from fastapi import Depends, status
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException, DatabaseError
from app.schemas.user_schema import UserCreate, UserLogin, UserResponseData, LoginResponseData,SortBy, Order
from app.models.user import User
from app.core.database import get_db
from app.core.responses import success_response, error_response
from app.core.auth import create_access_token, create_refresh_token
from app.core.schemas import PaginatedResponse
from passlib.context import CryptContext
from datetime import datetime, timezone
from sqlalchemy import asc, desc

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
            message="User registered successfully",
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

def get_all_users(
    page: int,
    per_page: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    account_type: Optional[str] = None,
    balance_min: Optional[float] = None,
    balance_max: Optional[float] = None,
    sort_by: Optional[SortBy] = None,
    order: Optional[Order] = None,
    db: Session = None
):
    query = db.query(User)

    # Apply filters
    if username:
        query = query.filter(User.Username.ilike(f"%{username}%"))
    if email:
        query = query.filter(User.Email.ilike(f"%{email}%"))
    if account_type:
        query = query.filter(User.AccountType == account_type)
    if balance_min is not None:
        query = query.filter(User.Balance >= balance_min)
    if balance_max is not None:
        query = query.filter(User.Balance <= balance_max)

    # Apply sorting
    sort_field = {
        SortBy.user_id: User.UserID,
        SortBy.username: User.Username,
        SortBy.email: User.Email,
        SortBy.balance: User.Balance,
        SortBy.created_at: User.CreatedAt,
        SortBy.last_login: User.LastLogin
    }.get(sort_by, User.UserID)  # Default to UserID if sort_by is invalid

    sort_order = desc if order == Order.desc else asc
    query = query.order_by(sort_order(sort_field))

    # Pagination
    offset = (page - 1) * per_page
    users = query.offset(offset).limit(per_page).all()
    total_items = query.count()
    total_pages = (total_items + per_page - 1) // per_page

    return PaginatedResponse(
        success=True,
        message="Users retrieved successfully",
        data={"users": [UserResponseData.model_validate(u).model_dump() for u in users]},
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages
    ).model_dump()

def get_user_by_id(user_id: int, db: Session):
    user = db.query(User).filter(User.UserID == user_id).first()
    if not user:
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            details={}
        )
    return success_response(
        message="User retrieved successfully",
        data=UserResponseData.model_validate(user).model_dump()
    )