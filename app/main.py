import os
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.gzip import GZipMiddleware

from app.core.rate_limiter import limiter, custom_rate_limit_handler
from slowapi.errors import RateLimitExceeded
from app.core.exceptions import CustomHTTPException
from app.core.schemas import BaseResponse
from app.routes import admins, users, atm, rbac
from app.core.database import get_db

app = FastAPI(
    title="AUT Banking System",
    version="1.0.0",
    default_response_model=BaseResponse,
    description="Official API documentation for AUT Bank's backend services",
    responses={
        400: {"model": BaseResponse},
        401: {"model": BaseResponse},
        403: {"model": BaseResponse},
        404: {"model": BaseResponse},
        422: {"model": BaseResponse},
        429: {"model": BaseResponse},
        500: {"model": BaseResponse},
    },
)

# <========== Gzip Middleware ==========>
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses > 1KB

# <========== CORS Configuration ==========>
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# <========== Rate limiting middleware ==========>
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


# <========== Storing DB session in app state for use in rate limiter ==========>
@app.middleware("http")
async def add_db_to_request(request: Request, call_next):
    db = next(get_db())  # Get DB session
    request.state.db = db
    try:
        response = await call_next(request)
        db.commit()  # Commit only if successful
        return response
    except Exception as e:
        db.rollback()  # Rollback on any error
        raise e  # Re-raise for FastAPI to handle
    finally:
        db.close()  # Always close the session


# <========== API routes ==========>
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["User"],
    responses={404: {"description": "Not found"}},
)
app.include_router(
    admins.router,
    prefix="/api/v1/admins",
    tags=["Admin"],
    responses={404: {"description": "Not found"}},
)
app.include_router(
    atm.router,
    prefix="/api/v1/atm",
    tags=["ATM"],
    responses={404: {"description": "Not found"}},
)
app.include_router(
    rbac.router,
    prefix="/api/v1/rbac",
    tags=["RBAC"],
    responses={404: {"description": "Not found"}},
)


# <========== Exception Handlers ==========>
# Custom exception handler
@app.exception_handler(CustomHTTPException)
async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": exc.detail.get("success", False),
            "message": exc.detail.get("message", "An error occurred"),
            "data": exc.detail.get("data", {}),
            "status_code": exc.status_code,
        },
    )


# Generic HTTPException handler for rate limiting and other cases
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": (
                exc.detail.get("message")
                if isinstance(exc.detail, dict)
                else str(exc.detail)
            ),
            "data": exc.detail.get("data") if isinstance(exc.detail, dict) else None,
            "status_code": exc.status_code,
        },
        headers=exc.headers,
    )


# <========== System Endpoints ==========>
# Health check endpoint with rate limit
@app.get("/health", tags=["System"], response_model=BaseResponse)
@limiter.limit(os.getenv("RATE_LIMIT_PUBLIC", "1000/hour"))
async def health_check(request: Request):
    return {
        "success": True,
        "message": "System is healthy",
        "status_code": status.HTTP_200_OK,
    }


# Root endpoint with rate limit
@app.get("/", response_model=BaseResponse, tags=["System"])
@limiter.limit(os.getenv("RATE_LIMIT_PUBLIC", "1000/hour"))
async def root(request: Request):
    return {
        "success": True,
        "message": "Welcome to AUT Bank API. Access /docs or /redoc for documentation.",
        "data": {
            "version": app.version,
            "documentation": {"swagger": "/docs", "redoc": "/redoc"},
        },
        "status_code": status.HTTP_200_OK,
    }


# <========== Application Startup ==========>
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))  # Default to 1 worker for dev
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        reload=os.getenv("RELOAD", "false").lower() == "true",  # Auto-reload in dev
    )
