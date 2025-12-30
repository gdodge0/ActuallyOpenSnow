# Mountain Weather

A stable, typed Python API for fetching mountain-relevant weather forecasts using Open-Meteo.

## Features

- **Multiple forecast models**: GFS, IFS, AIFS with easy model selection
- **Mountain-focused variables**: Temperature, wind, snow, precipitation, freezing level
- **Built-in caching**: Request caching via `requests-cache` for efficient API usage
- **Automatic retries**: Exponential backoff with `retry-requests`
- **Unit conversions**: Temperature (C/F/K), wind (km/h, m/s, mph, kn), precipitation (mm/in)
- **Range queries**: Get totals over datetime or timedelta windows
- **Typed data models**: Easy serialization for web backends
- **Forecast equivalence**: Compare forecasts by location, model, and run time

## Installation

```bash
pip install mountain-weather
```

Or install from source:

```bash
git clone https://github.com/example/mountain-weather.git
cd mountain-weather
pip install -e ".[dev]"
```

## Quick Start

```python
from weather import MeteoClient

# Create client with default settings (caching + retries enabled)
client = MeteoClient()

# Get forecast for Jackson Hole, WY
forecast = client.get_forecast(
    lat=43.4799,
    lon=-110.7624,
    model="gfs",
    elevation=3185,  # Summit elevation in meters
)

# Access hourly data with unit conversion
temps = forecast.get_temperature_2m(unit="F")
print(f"Temperature: {temps.values[:6]} {temps.unit}")

winds = forecast.get_wind_speed_10m(unit="mph")
print(f"Wind: {winds.values[:6]} {winds.unit}")

# Get snow totals for next 48 hours
from datetime import timedelta
snow_total = forecast.get_snowfall_total(
    unit="in",
    start=timedelta(hours=0),
    end=timedelta(hours=48),
)
print(f"48hr snowfall: {snow_total.value:.1f} {snow_total.unit}")

# Check forecast metadata
print(f"Model: {forecast.model_id}")
print(f"Model run: {forecast.model_run_utc}")
print(f"Elevation: {forecast.elevation_m}m")
```

## Available Models

| Model | ID | Max Horizon | Resolution |
|-------|-----|-------------|------------|
| GFS (NOAA) | `gfs` | 16 days | 0.25° |
| IFS (ECMWF) | `ifs` | 10 days | 0.25° |
| AIFS (ECMWF AI) | `aifs` | 15 days | 0.25° |

## API Reference

### MeteoClient

```python
client = MeteoClient(
    cache_expire_after=3600,  # Cache TTL in seconds (default: 1 hour)
    max_retries=3,            # Max retry attempts (default: 3)
    backoff_factor=0.5,       # Backoff multiplier (default: 0.5)
)

forecast = client.get_forecast(
    lat=43.4799,
    lon=-110.7624,
    model="gfs",              # Model ID (default: "gfs")
    elevation=3185,           # Optional elevation override in meters
    temperature_unit="C",     # Unit preference for temperature
    wind_speed_unit="kmh",    # Unit preference for wind
    precipitation_unit="mm",  # Unit preference for precip/snow
)
```

### Forecast

The `Forecast` object contains all forecast data and metadata:

```python
# Metadata
forecast.lat              # Requested latitude
forecast.lon              # Requested longitude
forecast.api_lat          # API-returned latitude
forecast.api_lon          # API-returned longitude
forecast.elevation_m      # Elevation in meters
forecast.model_id         # Model identifier
forecast.model_run_utc    # Model run timestamp (UTC)
forecast.times_utc        # List of forecast timestamps

# Hourly series getters (return Series with values and unit)
forecast.get_temperature_2m(unit="C")
forecast.get_wind_speed_10m(unit="kmh")
forecast.get_wind_gusts_10m(unit="kmh")
forecast.get_snowfall(unit="mm")
forecast.get_precipitation(unit="mm")
forecast.get_freezing_level_height(unit="m")

# Accumulated series
forecast.get_snowfall_accumulated(unit="mm")
forecast.get_precipitation_accumulated(unit="mm")

# Range totals (return Quantity with value and unit)
forecast.get_snowfall_total(unit="in", start=..., end=...)
forecast.get_precipitation_total(unit="mm", start=..., end=...)
```

### Range Queries

Range queries accept `datetime` (UTC) or `timedelta` offsets:

```python
from datetime import datetime, timedelta, timezone

# Using timedelta (offset from forecast start)
snow = forecast.get_snowfall_total(
    start=timedelta(hours=0),
    end=timedelta(hours=72),
)

# Using datetime (UTC)
snow = forecast.get_snowfall_total(
    start=datetime(2024, 1, 15, 0, tzinfo=timezone.utc),
    end=datetime(2024, 1, 18, 0, tzinfo=timezone.utc),
)
```

Ranges are `[start, end)` (inclusive start, exclusive end) and clamp to available data.

### Forecast Equivalence

Two forecasts are considered equivalent if they:
- Are within 100 meters (haversine distance)
- Use the same model
- Have the same model run time

```python
forecast1 = client.get_forecast(43.48, -110.76, model="gfs")
forecast2 = client.get_forecast(43.48, -110.76, model="gfs")

if forecast1.is_equivalent(forecast2):
    print("Forecasts are equivalent")
```

## Unit System

### Supported Units

| Category | Units |
|----------|-------|
| Temperature | `C`, `F`, `K` |
| Wind Speed | `kmh`, `ms`, `mph`, `kn` |
| Precipitation/Snow | `mm`, `cm`, `in`, `ft` |
| Elevation | `m`, `ft` |

### Unit Conversion

All getters accept a `unit` parameter for automatic conversion:

```python
# Temperature in different units
forecast.get_temperature_2m(unit="C")  # Celsius
forecast.get_temperature_2m(unit="F")  # Fahrenheit
forecast.get_temperature_2m(unit="K")  # Kelvin

# Wind in different units
forecast.get_wind_speed_10m(unit="kmh")  # km/h
forecast.get_wind_speed_10m(unit="mph")  # mph
forecast.get_wind_speed_10m(unit="ms")   # m/s
forecast.get_wind_speed_10m(unit="kn")   # knots
```

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=weather --cov-report=html
```

## License

MIT License - see LICENSE for details.

