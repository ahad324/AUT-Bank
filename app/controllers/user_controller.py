from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user_schema import UserCreate, UserResponse
from app.models.user import User
from app.core.database import get_db
from passlib.context import CryptContext
from datetime import datetime

router = APIRouter()


# ✅ Initialize bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # ✅ Check if Email, CNIC, or Username already exists
    existing_user = (
        db.query(User)
        .filter((User.Email == user.Email) | (User.CNIC == user.CNIC) | (User.Username == user.Username))
        .first()
    )

    if existing_user:
        if existing_user.Email == user.Email:
            raise HTTPException(status_code=400, detail="Email already registered. Please use a different email.")
        if existing_user.CNIC == user.CNIC:
            raise HTTPException(status_code=400, detail="CNIC already registered. Please use a different CNIC.")
        if existing_user.Username == user.Username:
            raise HTTPException(status_code=400, detail="Username already taken. Please choose another username.")

    # ✅ Hash password before saving
    hashed_password = pwd_context.hash(user.Password)

    # ✅ Convert date to datetime
    date_of_birth = datetime.combine(user.DateOfBirth, datetime.min.time())

    new_user = User(
        Username=user.Username,
        CNIC=user.CNIC,
        Email=user.Email,
        PasswordHash=hashed_password,
        AccountType=user.AccountType,
        DateOfBirth=date_of_birth
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return new_user

@router.post("/login")
def login_user(email: str, password: str, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.Email == email).first()
    if not user or not pwd_context.verify(password, user.PasswordHash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful", "user_id": user.UserID, "username": user.Username}
