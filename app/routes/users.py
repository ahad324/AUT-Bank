from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.controllers.user_controller import register_user, login_user
from app.schemas.user_schema import UserCreate, UserLogin, UserResponse
from app.core.database import get_db

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register(user: UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@router.post("/login", response_model=UserResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    return login_user(credentials, db)