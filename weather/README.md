# Weather API Library

Python library for fetching and processing weather forecasts from Open-Meteo.

## Overview

A clean, typed Python library that provides:
- Multi-model weather forecast fetching
- Automatic request caching and retries
- Unit conversions and data transformations
- Structured forecast data with type hints

## Installation

```bash
# From the weather directory
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

```python
from weather import MeteoClient

# Create client (with 30-minute cache)
client = MeteoClient(cache_expire_after=1800)

# Fetch a forecast
forecast = client.get_forecast(
    lat=43.5872,
    lon=-110.8281,
    model="gfs",
    elevation=3185,
)

# Access data
print(f"Location: {forecast.lat}, {forecast.lon}")
print(f"Model: {forecast.model_id}")
print(f"Hours: {len(forecast.times_utc)}")

# Get snowfall totals
snowfall = forecast.get_snowfall()
print(f"Total snowfall: {snowfall.total()}")

# Get temperature series
temps = forecast.get_temperature_2m(unit="F")
print(f"Current temp: {temps.values[0]}°F")
```

## Available Models

| Model ID | Name | Provider | Resolution |
|----------|------|----------|------------|
| `gfs` | GFS | NOAA | 0.25° |
| `ifs` | IFS | ECMWF | 0.25° |
| `aifs` | AIFS | ECMWF | 0.25° |
| `icon` | ICON | DWD | 0.125° |
| `jma` | JMA | JMA | 0.25° |
| `gem` | GEM | ECCC | 0.25° |
| `ukmo` | UKMO | Met Office | 0.25° |

## API Reference

### MeteoClient

```python
client = MeteoClient(
    cache_expire_after=3600,  # Cache TTL in seconds
    max_retries=3,            # Retry attempts
    backoff_factor=0.5,       # Retry backoff
    timeout=30,               # Request timeout
)
```

### get_forecast()

```python
forecast = client.get_forecast(
    lat=40.5884,              # Latitude (-90 to 90)
    lon=-111.6387,            # Longitude (-180 to 180)
    model="gfs",              # Model ID
    elevation=3216,           # Optional elevation override (meters)
    temperature_unit="celsius",
    wind_speed_unit="kmh",
    precipitation_unit="mm",
)
```

### Forecast Object

```python
# Metadata
forecast.lat                  # Requested latitude
forecast.lon                  # Requested longitude
forecast.api_lat              # Actual API grid latitude
forecast.api_lon              # Actual API grid longitude
forecast.elevation_m          # Elevation in meters
forecast.model_id             # Weather model used
forecast.model_run_utc        # Model run timestamp

# Time series
forecast.times_utc            # List of ISO timestamps
forecast.hourly_data          # Dict of variable → values
forecast.hourly_units         # Dict of variable → unit

# Helper methods
forecast.get_temperature_2m(unit="C")  # Temperature series
forecast.get_snowfall(unit="cm")       # Snowfall series
forecast.get_snowfall_total(hours=72)  # Total snowfall
forecast.to_dict()                     # Serialize to dict
```

### Series Object

```python
series = forecast.get_snowfall()

series.values      # List of hourly values
series.unit        # Unit string (e.g., "cm")
series.total()     # Sum of all values
series.max()       # Maximum value
series.min()       # Minimum value
series.mean()      # Average value
```

## Project Structure

```
weather/
├── src/weather/
│   ├── __init__.py        # Public API exports
│   ├── clients/
│   │   ├── base.py        # Base client class
│   │   └── openmeteo.py   # Open-Meteo implementation
│   ├── config/
│   │   ├── defaults.py    # Default settings
│   │   └── models.py      # Model configurations
│   ├── domain/
│   │   ├── errors.py      # Exception classes
│   │   ├── forecast.py    # Forecast dataclass
│   │   └── quantities.py  # Series/Quantity types
│   └── parsing/
│       └── openmeteo_parser.py
├── examples/
│   └── jackson_hole_aifs.py
├── pyproject.toml
└── README.md
```

## Examples

### Compare Models

```python
from weather import MeteoClient

client = MeteoClient()
models = ["gfs", "ifs", "aifs"]

for model_id in models:
    forecast = client.get_forecast(
        lat=43.5872,
        lon=-110.8281,
        model=model_id,
    )
    snowfall = forecast.get_snowfall_total(hours=72)
    print(f"{model_id.upper()}: {snowfall:.1f} cm")
```

### Custom Variables

```python
from weather import MeteoClient
from weather.config.defaults import DEFAULT_HOURLY_VARIABLES

# Add additional variables
variables = DEFAULT_HOURLY_VARIABLES + (
    "soil_temperature_0cm",
    "soil_moisture_0_to_1cm",
)

client = MeteoClient(hourly_variables=variables)
forecast = client.get_forecast(lat=40.0, lon=-105.0, model="gfs")

# Access custom variable
soil_temp = forecast.hourly_data.get("soil_temperature_0cm")
```

### Serialization

```python
import json
from weather import MeteoClient

client = MeteoClient()
forecast = client.get_forecast(lat=40.0, lon=-105.0, model="gfs")

# Convert to dict
data = forecast.to_dict()

# Save to JSON
with open("forecast.json", "w") as f:
    json.dump(data, f, indent=2, default=str)
```

## Error Handling

```python
from weather import MeteoClient, ApiError, ModelError

client = MeteoClient()

try:
    forecast = client.get_forecast(lat=40.0, lon=-105.0, model="invalid")
except ModelError as e:
    print(f"Invalid model: {e}")
except ApiError as e:
    print(f"API error: {e}")
```

## Caching

The library uses `requests-cache` for automatic caching:

```python
# Cache stored in .weather_cache SQLite database
client = MeteoClient(cache_expire_after=3600)  # 1 hour

# Clear cache manually
client.clear_cache()
```

## Data Sources

All data from [Open-Meteo](https://open-meteo.com/):
- Free for non-commercial use
- No API key required
- Global coverage
- Hourly resolution

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/weather
```
