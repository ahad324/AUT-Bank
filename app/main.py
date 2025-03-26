import os
from fastapi import FastAPI
import uvicorn
from app.routes import users

app = FastAPI(title="Secure Banking System")

# Include API routes
app.include_router(users.router, prefix="/users", tags=["Users"])

@app.get("/")
def root():
    return {"message": "Welcome to Secure Banking API"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT
    uvicorn.run(app, host="0.0.0.0", port=port)