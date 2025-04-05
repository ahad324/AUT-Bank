# app/core/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, Depends
from app.core.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.admin import Admin
import os
from redis import Redis
from typing import Optional

# Singleton Redis client
redis_client = None


def get_redis_client() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return redis_client


# Custom key function for rate limiting
def get_rate_limit_key(request: Request) -> str:
    """
    Determines the rate limit key based on authentication status:
    - Authenticated users: 'user:<UserID>'
    - Authenticated admins: 'admin:<AdminID>'
    - Unauthenticated: 'ip:<client_ip>'
    """
    auth_header = request.headers.get("Authorization")

    # Check for authenticated user
    if request.url.path.startswith("/api/v1/users") and auth_header:
        try:
            token = auth_header.split("Bearer ")[1]
            user: User = get_current_user(token, request.state.db)
            return f"user:{user.UserID}"
        except (IndexError, AttributeError, HTTPException):
            pass

    # Check for authenticated admin
    elif request.url.path.startswith("/api/v1/admins") and auth_header:
        try:
            token = auth_header.split("Bearer ")[1]
            admin: Admin = get_current_admin(token, request.state.db)
            return f"admin:{admin.AdminID}"
        except (IndexError, AttributeError, HTTPException):
            pass

    # Fallback to IP for public endpoints
    return f"ip:{get_remote_address(request)}"


# Initialize Limiter with Redis backend
limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    default_limits=["100/hour"],  # Fallback for unannotated endpoints
    enabled=True,
)


# Custom handler for 429 responses
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom handler for rate limit exceeded responses.
    Raises an HTTPException with retry-after time from Redis TTL.
    """
    key = get_rate_limit_key(request)
    redis = get_redis_client()
    ttl = redis.ttl(f"{key}:rate_limit")  # Get TTL
    retry_after = ttl if ttl > 0 else 60  # Use TTL if positive, else default to 60
    raise HTTPException(
        status_code=429,
        detail={
            "success": False,
            "message": "Too many requests. Please try again later.",
            "data": {"retry_after": retry_after},
        },
        headers={"Retry-After": str(retry_after)},
    )


def get_limiter() -> Limiter:
    return limiter
