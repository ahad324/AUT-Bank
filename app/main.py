import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .routes import users
from .core.exceptions import CustomHTTPException
from .core.responses import StandardResponse

app = FastAPI(
    title="AUT Banking System",
    version="1.0.0",
    description="Official API documentation for AUT Bank's backend services",
    responses={
        400: {"model": StandardResponse},
        401: {"model": StandardResponse},
        403: {"model": StandardResponse},
        404: {"model": StandardResponse},
        422: {"model": StandardResponse},
        500: {"model": StandardResponse}
    }
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["User Management"],
    responses={404: {"description": "Not found"}}
)

# Custom exception handler
@app.exception_handler(CustomHTTPException)
async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )

# Health check endpoint
@app.get(
    "/health",
    tags=["System"],
    response_model=StandardResponse,
    summary="System health check"
)
async def health_check():
    return {
        "success": True,
        "message": "System is healthy",
        "status_code": status.HTTP_200_OK
    }

# Root endpoint with standardized response
@app.get(
    "/",
    response_model=StandardResponse,
    tags=["System"],
    summary="API Welcome"
)
def root():
    return {
        "success": True,
        "message": "Welcome to AUT Bank API. Access /docs or /redoc for documentation.",
        "data": {
            "version": app.version,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc"
            }
        },
        "status_code": status.HTTP_200_OK
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))  # Default to 1 worker for dev
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        reload=os.getenv("RELOAD", "false").lower() == "true"  # Auto-reload in dev
    )