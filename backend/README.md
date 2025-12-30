# ActuallyOpenSnow Backend

FastAPI REST API server for the ActuallyOpenSnow weather application.

## Overview

The backend provides a REST API that wraps the weather library, adding:
- Resort database with 70+ Ikon/Epic pass resorts
- Multi-model blend forecasting
- Response caching for performance
- Batch endpoints for efficient data loading

## Requirements

- Python 3.11+
- Dependencies in `requirements.txt`

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Running

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### Resorts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/resorts` | List all resorts |
| GET | `/api/resorts?state=CO` | Filter by state |
| GET | `/api/resorts/{slug}` | Get resort details |
| GET | `/api/resorts/{slug}/forecast` | Get resort forecast |
| GET | `/api/resorts/{slug}/compare` | Compare models for resort |
| GET | `/api/resorts/batch/forecast` | Batch fetch multiple resorts |

### Forecasts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/forecast` | Forecast by coordinates |
| GET | `/api/compare` | Compare models by coordinates |

**Query Parameters:**
- `model`: Weather model ID (default: `blend`)
- `elevation`: `summit`, `base`, or meters
- `lat`, `lon`: Coordinates (for `/api/forecast`)

### Models

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List available models |
| GET | `/api/models/{id}` | Get model details |

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/blend/config` | View blend weights |
| GET | `/api/cache/stats` | Cache statistics |
| POST | `/api/cache/clear` | Clear all caches |

## Blend Model

The blend model averages forecasts from multiple weather models with configurable weights:

```python
BLEND_MODEL_WEIGHTS = {
    "gfs": 2.0,    # NOAA GFS - 2x weight
    "ifs": 2.0,    # ECMWF IFS - 2x weight
    "aifs": 2.0,   # ECMWF AIFS - 2x weight
    "icon": 1.0,   # DWD ICON - 1x weight
    "jma": 1.0,    # JMA - 1x weight
}
```

Configure via environment variables:
```bash
export BLEND_WEIGHT_GFS=2.0
export BLEND_WEIGHT_IFS=2.0
export BLEND_WEIGHT_AIFS=2.0
export BLEND_WEIGHT_ICON=1.0
export BLEND_WEIGHT_JMA=1.0
```

## Caching

The backend implements multiple caching layers:

1. **Open-Meteo Cache**: Raw API responses cached for 30 minutes
2. **Blend Cache**: Computed blend forecasts cached for 30 minutes

Cache is automatically invalidated when:
- TTL expires
- Server restarts
- `/api/cache/clear` is called

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI application & routes
│   ├── models.py      # Pydantic models
│   └── resorts.py     # Resort database
├── requirements.txt
├── Dockerfile
└── README.md
```

## Docker

```bash
# Build
docker build -t actuallyopensnow-backend -f Dockerfile ..

# Run
docker run -p 8000:8000 actuallyopensnow-backend
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHONUNBUFFERED` | 1 | Disable output buffering |
| `BLEND_WEIGHT_*` | varies | Model blend weights |

## Adding Resorts

Edit `app/resorts.py` to add new resorts:

```python
Resort(
    slug="resort-slug",
    name="Resort Name",
    state="CO",
    country="US",
    lat=39.1234,
    lon=-106.5678,
    base_elevation_m=2500,
    summit_elevation_m=3500,
),
```

## Error Handling

The API returns standard HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found
- `502`: Upstream API error
- `503`: Service unavailable

