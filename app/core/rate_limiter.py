from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, Depends
from app.core.auth import get_current_user, get_current_admin
from app.models.user import User
from app.models.admin import Admin
import os
from redis import Redis
from typing import Optional, Any
import json

# Singleton Redis client
redis_client = None

# Load cache TTLs from environment with defaults
CACHE_TTL_SHORT = int(
    os.getenv("REDIS_CACHE_TTL_SHORT", "300")
)  # 5 min for volatile data
CACHE_TTL_MEDIUM = int(
    os.getenv("REDIS_CACHE_TTL_MEDIUM", "3600")
)  # 1 hr for semi-static
CACHE_TTL_LONG = int(os.getenv("REDIS_CACHE_TTL_LONG", "86400"))  # 24 hr for static


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
    auth_header = request.headers.get("Authorization")
    if request.url.path.startswith("/api/v1/users") and auth_header:
        try:
            token = auth_header.split("Bearer ")[1]
            user: User = get_current_user(token, request.state.db)
            return f"user:{user.UserID}"
        except (IndexError, AttributeError, HTTPException):
            pass
    elif request.url.path.startswith("/api/v1/admins") and auth_header:
        try:
            token = auth_header.split("Bearer ")[1]
            admin: Admin = get_current_admin(token, request.state.db)
            return f"admin:{admin.AdminID}"
        except (IndexError, AttributeError, HTTPException):
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    default_limits=["100/hour"],
    enabled=True,
)


async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    key = get_rate_limit_key(request)
    redis = get_redis_client()
    ttl = redis.ttl(f"{key}:rate_limit") or 60
    raise HTTPException(
        status_code=429,
        detail={
            "success": False,
            "message": "Too many requests. Please try again later.",
            "data": {"retry_after": ttl},
        },
        headers={"Retry-After": str(ttl)},
    )


def get_limiter() -> Limiter:
    return limiter


# Caching Utilities
def get_cache_key(
    request: Request, endpoint: str, user_id: Optional[int] = None, params: dict = None
) -> str:
    """Generate a unique cache key based on endpoint, user, and query params."""
    base = f"{endpoint}"
    if user_id:
        base += f":user:{user_id}"
    if params:
        param_str = ":".join(
            f"{k}={v}" for k, v in sorted(params.items()) if v is not None
        )
        base += f":{param_str}"
    return base


def get_from_cache(key: str) -> Optional[Any]:
    """Retrieve data from Redis cache."""
    redis = get_redis_client()
    cached = redis.get(key)
    return json.loads(cached) if cached else None


def set_to_cache(key: str, value: Any, ttl: int) -> None:
    """Store data in Redis cache with specified TTL."""
    redis = get_redis_client()
    redis.setex(key, ttl, json.dumps(value))


def invalidate_cache(pattern: str) -> None:
    """Invalidate cache keys matching a pattern (e.g., 'users:*')."""
    redis = get_redis_client()
    keys = redis.keys(f"{pattern}*")
    if keys:
        redis.delete(*keys)
