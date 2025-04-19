# app/core/utils.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.exceptions import CustomHTTPException
from typing import TypeVar, Type

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

T = TypeVar("T")


def send_email(to_email: str, subject: str, body: str) -> None:
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
        raise CustomHTTPException(
            status_code=500,
            message="Email service not configured",
            details={"error": "Missing SMTP environment variables"},
        )

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
    except Exception as e:
        raise CustomHTTPException(
            status_code=500,
            message="Failed to send email",
            details={"error": str(e)},
        )


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
