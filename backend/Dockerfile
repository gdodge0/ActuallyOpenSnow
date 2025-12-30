# Backend Dockerfile - FastAPI + Python
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy weather package first (dependency)
COPY weather/pyproject.toml weather/README.md /app/weather/
COPY weather/src /app/weather/src

# Install weather package
RUN pip install /app/weather

# Copy backend requirements and install
COPY backend/requirements.txt /app/backend/
RUN pip install -r /app/backend/requirements.txt

# Copy backend application
COPY backend/app /app/backend/app

WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Health check using curl
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
