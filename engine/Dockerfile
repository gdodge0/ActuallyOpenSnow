# Engine Dockerfile - GRIB2 background processor
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies (eccodes for GRIB2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libeccodes-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy weather package (dependency)
COPY weather/pyproject.toml weather/README.md /app/weather/
COPY weather/src /app/weather/src

# Install weather package with herbie extras
RUN pip install "/app/weather[herbie]"

# Copy db package (shared ORM)
COPY db /app/db

# Copy backend app package (resort data needed for db seeding)
COPY backend/app /app/backend/app

# Copy engine requirements and install
COPY engine/requirements.txt /app/engine/
RUN pip install -r /app/engine/requirements.txt

# Copy engine application
COPY engine /app/engine

WORKDIR /app

# GRIB cache directory
RUN mkdir -p /data/grib-cache
ENV GRIB_CACHE_DIR=/data/grib-cache

# Run the scheduler
CMD ["python", "-m", "engine.scheduler"]
