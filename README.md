Secure Banking System API (FastAPI)

This is a professional and modular Secure Banking System built using FastAPI, designed with a clean architecture and robust features like role-based access control (RBAC), rate limiting with Redis, token-based authentication, and modular route/controller separation.

Features:
- FastAPI-powered asynchronous backend
- Modular structure (routes, controllers, schemas, core logic)
- Role-Based Access Control (RBAC)
- Redis-backed rate limiting via SlowAPI
- Secure authentication system with JWT tokens
- SQL Server database integration
- Admin and User support with different permissions
- Support for deposits, withdrawals, loans, card management, and more

Project Structure (partial):
controllers/
├── cards/, deposits/, loans/, transfers/, withdrawals/
├── admin_controller.py, user_controller.py, rbac_controller.py
core/
├── auth.py, database.py, rate_limiter.py, rbac.py, ...
models/
routes/
schemas/
main.py

Requirements:
- Python 3.10+
- Redis server
- SQL Server instance (hosted or local)
- pip install -r requirements.txt

Environment Variables:
Create a .env file in the root of your project and define the following variables:

DATABASE_URL="your_database_url"
PORT="8000"
WORKERS="4"
MAX_REQUESTS="1000"
TIMEOUT="120"
KEEPALIVE="60"
RELOAD="true"

# JWT Config
SECRET_KEY="699fa43efa4989910413cca9f6799c46d8bd2bfef80dad365b5d2c09134b602c"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES="3000"
REFRESH_TOKEN_EXPIRE_DAYS="7"

# CORS
ALLOWED_ORIGINS="*"

# Redis and Rate Limiting
REDIS_URL="redis://localhost:6379/0"
RATE_LIMIT_LOGIN="5/minute"
RATE_LIMIT_ADMIN_CRITICAL="10/minute"
RATE_LIMIT_USER_DEFAULT="100/hour"
RATE_LIMIT_PUBLIC="1000/hour"
RATE_LIMIT_EXPORT="5/hour"

Generating a Secure SECRET_KEY:
To generate a new SECRET_KEY, run this command:
python -c "import secrets; print(secrets.token_hex(32))"

Running the App:
Start the app with:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Or use environment configurations:
uvicorn main:app --host 0.0.0.0 --port $PORT --workers $WORKERS --limit-max-requests $MAX_REQUESTS --timeout-keep-alive $KEEPALIVE --reload

Note:
Make sure Redis is running on your machine (redis-server) before launching the app to avoid errors with rate limiting.