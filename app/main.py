from fastapi import FastAPI
from app.routes import users

app = FastAPI(title="Secure Banking System")

# Include API routes
app.include_router(users.router, prefix="/users", tags=["Users"])

@app.get("/")
def root():
    return {"message": "Welcome to Secure Banking API"}
