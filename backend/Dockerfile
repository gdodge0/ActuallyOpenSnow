# Backend Dockerfile - FastAPI + Python
# Optimized for Coolify deployment

FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
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

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Coolify will handle external mapping)
EXPOSE 8000

# Health check for Coolify
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run the application - bind to 0.0.0.0 for container networking
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
