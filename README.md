
# AUT Bank API 🏦

Welcome to the **AUT Bank API**, a powerful and secure backend service crafted by **AbdulAhad** to empower modern banking applications. Built with **FastAPI**, **SQLAlchemy**, and **Microsoft SQL Server**, this API offers a comprehensive suite of banking functionalities, including user management, transactions, loans, cards, and role-based access control (RBAC). This README provides an overview of the project, its features, setup instructions, and usage guidelines.

## Table of Contents 📋

- [Project Overview](#project-overview) 🌟
- [Key Features](#key-features) 🚀
- [Technologies Used](#technologies-used) 🛠️
- [Directory Structure](#directory-structure) 📂
- [Installation](#installation) ⚙️
- [Configuration](#configuration) 🔧
- [Running the Application](#running-the-application) ▶️
- [Running with Docker Compose](#running-with-docker-compose) 🐳
- [API Documentation](#api-documentation) 📚
- [Authentication](#authentication) 🔐
- [Rate Limiting](#rate-limiting) ⏱️
- [WebSocket Support](#websocket-support) 🌐
- [Caching](#caching) 💾
- [Contributing](#contributing) 🤝

## Project Overview 🌟

The **AUT Bank API**, developed by **AbdulAhad**, serves as the backbone for a banking system, enabling seamless management of users, admins, transactions, loans, cards, and deposits. It incorporates modern web development practices, including RESTful API design, JWT-based authentication, rate limiting, and WebSocket for real-time updates. The API is highly modular, with separate controllers, models, schemas, and routes for each feature, ensuring maintainability and scalability.

## Key Features 🚀

- **User Management** 👤:
  - User registration, login, and profile management.
  - Admin management with role-based permissions.
  - Toggle user account status (active/inactive).
- **Transaction Management** 💸:
  - Support for deposits, withdrawals, and transfers.
  - Transaction history with filtering and pagination.
  - Export transactions to CSV for reporting.
- **Card Management** 💳:
  - Create, update, block, and unblock user cards.
  - Card status tracking (Approved, Inactive, Blocked).
- **Loan Management** 📈:
  - Apply for loans, approve/reject loans, and make loan payments.
  - View loan types and payment history.
- **Role-Based Access Control (RBAC)** 🔒:
  - Create, update, and delete roles and permissions.
  - Assign permissions to roles and manage admin access.
- **Analytics** 📊:
  - Summary of user activity, transaction volumes, and loan statistics.
  - Real-time analytics for admins and users.
- **WebSocket Support** 📡:
  - Real-time notifications for users and admins.
- **Security** 🛡️:
  - JWT-based authentication with access and refresh tokens.
  - Password hashing using bcrypt.
  - Rate limiting to prevent abuse.
- **Caching** ⚡:
  - Redis-based caching for frequently accessed data to enhance performance.

## Technologies Used 🛠️

- **Backend Framework**: FastAPI 🌐
- **Database**: Microsoft SQL Server with SQLAlchemy ORM 🗄️
- **Authentication**: JWT (JSON Web Tokens) 🔑
- **Password Hashing**: Passlib (bcrypt) 🔒
- **Caching**: Redis 💾
- **Rate Limiting**: SlowAPI ⏱️
- **WebSocket**: FastAPI WebSocket support 📡
- **Middleware**: CORS, GZip compression 🌍
- **Validation**: Pydantic for data validation ✅
- **Environment Management**: Python-dotenv ⚙️
- **Server**: Uvicorn 🚀

## Directory Structure 📂

The project is organized into a modular structure to promote separation of concerns:

```
AUT-Bank/
├── controllers/               # Business logic for various modules
│   ├── admin_controller.py
│   ├── cards/
│   ├── deposits/
│   ├── loans/
│   ├── rbac_controller.py
│   ├── transactions/
│   ├── transfers/
│   ├── user_controller.py
│   ├── withdrawals/
├── core/                      # Core utilities and configurations
│   ├── auth.py
│   ├── database.py
│   ├── event_emitter.py
│   ├── exceptions.py
│   ├── rate_limiter.py
│   ├── rbac.py
│   ├── responses.py
│   ├── schemas.py
│   ├── utils.py
│   ├── websocket_manager.py
├── models/                    # SQLAlchemy database models
│   ├── admin.py
│   ├── card.py
│   ├── deposit.py
│   ├── loan.py
│   ├── rbac.py
│   ├── transfer.py
│   ├── user.py
│   ├── withdrawal.py
├── routes/                    # API route definitions
│   ├── admins.py
│   ├── atm.py
│   ├── rbac.py
│   ├── users.py
│   ├── websocket.py
├── schemas/                   # Pydantic schemas for request/response validation
│   ├── admin_schema.py
│   ├── card_schema.py
│   ├── deposit_schema.py
│   ├── loan_schema.py
│   ├── rbac_schema.py
│   ├── transfer_schema.py
│   ├── user_schema.py
│   ├── withdrawal_schema.py
├── main.py                    # Application entry point
├── README.md                  # Project documentation
```

## Installation ⚙️

Follow these steps to set up the AUT Bank API locally:

### Prerequisites

- Python 3.9+ 🐍
- Microsoft SQL Server 🗄️
- Redis 💾
- Git 🌿

### Steps

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/ahad324/AUT-Bank.git
   cd aut-bank-api
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Microsoft SQL Server**:
   - Create a database in SQL Server:
     ```sql
     CREATE DATABASE aut_bank;
     ```
   - Update the database URL in the `.env` file (see [Configuration](#configuration)).

5. **Set Up Redis**:
   - Install and run Redis locally or use a hosted Redis service.
   - Update the Redis URL in the `.env` file.

## Configuration 🔧

Create a `.env` file in the project root with the following environment variables:

```env
# Database Configuration
DATABASE_URL=mssql+pyodbc://username:password@server/aut_bank?driver=ODBC+Driver+17+for+SQL+Server

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# JWT Configuration
SECRET_KEY=your-secret-key
ALGORITHM=HS256

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://example.com

# Rate Limiting
RATE_LIMIT_PUBLIC=1000/hour
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_ADMIN_CRITICAL=10/minute
RATE_LIMIT_USER_DEFAULT=100/hour
RATE_LIMIT_EXPORT=5/hour

# Server Configuration
PORT=8000
WORKERS=1
RELOAD=true  # Set to false in production
```

Generate a secure `SECRET_KEY` for JWT using a tool like `openssl`:

```bash
openssl rand -hex 32
```

## Running the Application ▶️

1. **Apply Database Migrations** (if using a migration tool like Alembic):
   ```bash
   alembic upgrade head
   ```

2. **Start the Application**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Access the API**:
   - The API will be available at `http://localhost:8000`.
   - Interactive API documentation is available at:
     - Swagger UI: `http://localhost:8000/docs` 📘
     - ReDoc: `http://localhost:8000/redoc` 📙

# Running with Docker Compose 🐳

For a hassle-free setup, you can run the **AUT Bank API** using Docker Compose, which includes the application and Redis (with RedisInsight UI) in a single command. The database is hosted on **somee.com**, so you only need to provide the database connection string.

---

## Prerequisites

- Docker and Docker Compose installed 🐳  
- Access to the somee.com database credentials 🌐

---

## Steps

### 1. Clone the Repository

```bash
git clone https://github.com/ahad324/AUT-Bank.git
cd AUT-Bank
```
## 2. Set Up Environment Variables

Create a `.env` file in the project root with the following content:

```bash
echo 'DATABASE_URL=mssql+pyodbc://your_username:your_password@yourdb.somee.com:1433/your_db_name?driver=ODBC+Driver+17+for+SQL+Server' > .env
echo 'REDIS_URL=redis://redis:6379' >> .env
```
> Replace `your_username`, `your_password`, `yourdb.somee.com`, and `your_db_name` with your somee.com database credentials.

---

## 3. Run the Application

Start the application and Redis:

```bash
docker-compose up --build
```
This pulls the `royal332/aut-bank:latest` image, starts the Redis Stack server and UI, and runs the API.

---

## 4. Access the Application and Redis UI

- **API:** [http://localhost:8000](http://localhost:8000)
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) 📘
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc) 📙
- **RedisInsight UI:** [http://localhost:8001](http://localhost:8001) _(may take a moment to load)_
## 5. View Logs (if needed)

```bash
docker-compose logs
```
## 5. Stop the Application

```bash
docker-compose down
```

## API Documentation 📚

The AUT Bank API provides interactive documentation via Swagger UI and ReDoc. Key endpoints include:

- **User Routes** (`/api/v1/users`) 👥:
  - Register, login, manage profile, apply for loans, manage cards, and transfer funds.
- **Admin Routes** (`/api/v1/admins`) 🛠️:
  - Manage admins, users, loans, cards, and transactions.
- **ATM Routes** (`/api/v1/atm`) 🏧:
  - Process withdrawals via card and PIN.
- **RBAC Routes** (`/api/v1/rbac`) 🔐:
  - Manage roles, permissions, and role-permission assignments.
- **WebSocket Routes** (`/api/v1/ws`) 📡:
  - Real-time notifications for users and admins.

For detailed endpoint information, refer to the Swagger UI at `/docs`.

## Authentication 🔐

The API uses **JWT-based authentication** with access and refresh tokens. Key authentication endpoints:

- **User Login**: `POST /api/v1/users/login` 🔑
- **Admin Login**: `POST /api/v1/admins/login` 🔑
- **Token Refresh**: `POST /api/v1/users/refresh` 🔄

Tokens must be included in the `Authorization` header as `Bearer <token>` for protected routes.

## Rate Limiting ⏱️

The API implements rate limiting using **SlowAPI** to prevent abuse. Configurable limits are defined in the `.env` file, such as:

- Public endpoints: `1000/hour`
- Login attempts: `5/minute`
- Admin-critical operations: `10/minute`
- Export operations: `5/hour`

Rate limits are enforced per IP address and can be customized.

## WebSocket Support 🌐

The API supports real-time communication via WebSocket for both users and admins:

- **User WebSocket**: `/api/v1/ws/user?token=<jwt-token>` 📡
- **Admin WebSocket**: `/api/v1/ws/admin?token=<jwt-token>` 📡

WebSocket connections require a valid JWT token and are managed by the `ConnectionManager` class.

## Caching 💾

The API uses **Redis** for caching frequently accessed data to improve performance. Cache durations are configurable:

- **Short TTL**: 5 minutes (e.g., analytics, transactions)
- **Medium TTL**: 1 hour (e.g., user profiles, cards)
- **Long TTL**: 24 hours (e.g., roles, permissions)

Cache invalidation is triggered on data updates to ensure consistency.

## Contributing 🤝

Contributions to the AUT Bank API are welcome! To contribute:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure your code follows the project's coding standards and includes appropriate tests.

---

**AUT Bank API**, created by **AbdulAhad**, is designed to provide a secure, scalable, and efficient backend for banking applications.
