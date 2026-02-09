# Engine-Backend Dockerfile - Control API + Dashboard
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy weather package (dependency)
COPY weather/pyproject.toml weather/README.md /app/weather/
COPY weather/src /app/weather/src

# Install weather package
RUN pip install /app/weather

# Copy db package (shared ORM)
COPY db /app/db

# Copy engine-backend requirements and install
COPY engine-backend/requirements.txt /app/engine-backend/
RUN pip install -r /app/engine-backend/requirements.txt

# Copy engine-backend application
COPY engine-backend/app /app/engine-backend/app

WORKDIR /app/engine-backend

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8001/api/engine/status || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
