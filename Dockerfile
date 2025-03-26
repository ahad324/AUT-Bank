# Use Python 3.11 slim base image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

ENV WORKERS=4 \
    MAX_REQUESTS=1000 \
    TIMEOUT=120 \
    KEEPALIVE=60

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    g++ \
    unixodbc-dev \
    unixodbc \
    freetds-dev \
    freetds-bin \
    tdsodbc \
    gnupg2 \
    curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver 17 for SQL Server
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key --keyring /etc/apt/trusted.gpg.d/microsoft.gpg add - && \
    curl -sSL https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Production (Gunicorn + Uvicorn)
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker \
    --workers ${WORKERS} \
    --max-requests ${MAX_REQUESTS} \
    --timeout ${TIMEOUT} \
    --keep-alive ${KEEPALIVE} \
    --access-logfile - \
    --error-logfile - \
    --bind 0.0.0.0:${PORT} \
    --preload \
    app.main:app"]