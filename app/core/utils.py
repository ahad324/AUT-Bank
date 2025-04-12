# app/core/utils.py
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException
from typing import TypeVar, Type

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

T = TypeVar("T")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def check_unique_field(
    db: Session,
    model: Type[T],
    field_name: str,
    value: any,
    exclude_id: int | None = None,
) -> None:
    query = db.query(model).filter(getattr(model, field_name) == value)
    if exclude_id:
        query = query.filter(getattr(model, "id") != exclude_id)
    if query.first():
        raise CustomHTTPException(
            status_code=400, message=f"{field_name} {value} already exists"
        )
