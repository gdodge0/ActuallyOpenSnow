"""Parser for Open-Meteo API responses."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from weather.domain.forecast import Forecast
from weather.domain.errors import ApiError
from weather.units.openmeteo_units import decode_openmeteo_unit, get_default_unit
from weather.utils.time import infer_model_run_time

logger = logging.getLogger(__name__)


def parse_openmeteo_response(
    response: Any,
    requested_lat: float,
    requested_lon: float,
    model_id: str,
    elevation_override: float | None = None,
) -> Forecast:
    """Parse an Open-Meteo API response into a Forecast object.

    Supports both the JSON API response format and the openmeteo-requests
    library's response objects (which use FlatBuffers under the hood).

    Args:
        response: The API response (either dict from JSON API or
                  openmeteo_requests response object).
        requested_lat: The latitude that was requested.
        requested_lon: The longitude that was requested.
        model_id: The model ID that was used.
        elevation_override: Optional elevation override value.

    Returns:
        A Forecast object with parsed data.

    Raises:
        ApiError: If the response cannot be parsed.
    """
    try:
        # Handle openmeteo-requests library response objects
        if hasattr(response, "Latitude"):
            return _parse_flatbuffers_response(
                response,
                requested_lat,
                requested_lon,
                model_id,
                elevation_override,
            )

        # Handle raw JSON dict response
        if isinstance(response, dict):
            return _parse_json_response(
                response,
                requested_lat,
                requested_lon,
                model_id,
                elevation_override,
            )

        raise ApiError(f"Unknown response type: {type(response)}")

    except ApiError:
        raise
    except Exception as e:
        logger.exception("Failed to parse Open-Meteo response")
        raise ApiError(f"Failed to parse response: {e}")


def _parse_flatbuffers_response(
    response: Any,
    requested_lat: float,
    requested_lon: float,
    model_id: str,
    elevation_override: float | None,
) -> Forecast:
    """Parse a response from the openmeteo-requests library."""
    # Extract coordinates from response
    api_lat = response.Latitude()
    api_lon = response.Longitude()

    # Extract elevation (use override if provided)
    elevation = elevation_override
    if elevation is None and hasattr(response, "Elevation"):
        elevation = response.Elevation()

    # Extract hourly data
    hourly = response.Hourly()
    if hourly is None:
        raise ApiError("No hourly data in response")

    # Parse time range
    time_start = hourly.Time()
    time_end = hourly.TimeEnd()
    interval = hourly.Interval()

    # Generate timestamps
    times_utc = []
    current_time = time_start
    while current_time < time_end:
        dt = datetime.fromtimestamp(current_time, tz=timezone.utc)
        times_utc.append(dt)
        current_time += interval

    # Extract variable data
    hourly_data: dict[str, tuple[float | None, ...]] = {}
    hourly_units: dict[str, str] = {}

    # Map of variable index to name (order matches request)
    variable_names = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_gusts_10m",
        "snowfall",
        "precipitation",
        "freezing_level_height",
    ]

    # Expected unit categories for each variable (for validation)
    expected_categories: dict[str, str] = {
        "temperature_2m": "temperature",
        "wind_speed_10m": "speed",
        "wind_gusts_10m": "speed",
        "snowfall": "length",
        "precipitation": "length",
        "freezing_level_height": "length",
    }

    for i, var_name in enumerate(variable_names):
        try:
            variable = hourly.Variables(i)
            if variable is not None:
                # Get values as numpy array, convert to tuple
                values_array = variable.ValuesAsNumpy()
                # Handle NaN values (convert to None)
                values = tuple(
                    None if (v != v) else float(v)  # NaN check: v != v
                    for v in values_array
                )
                hourly_data[var_name] = values

                # Get unit - validate it makes sense for this variable
                default_unit = get_default_unit(var_name)
                try:
                    unit_enum = variable.Unit()
                    decoded_unit = decode_openmeteo_unit(unit_enum)
                    
                    # Validate the unit category matches what we expect
                    from weather.units.normalize import get_unit_category
                    expected_cat = expected_categories.get(var_name)
                    actual_cat = get_unit_category(decoded_unit)
                    
                    if expected_cat and actual_cat != expected_cat and actual_cat != "undefined":
                        # Unit category mismatch - use default
                        logger.warning(
                            f"Unit category mismatch for {var_name}: got {decoded_unit} "
                            f"({actual_cat}), expected {expected_cat}. Using default: {default_unit}"
                        )
                        hourly_units[var_name] = default_unit
                    else:
                        hourly_units[var_name] = decoded_unit
                        
                except (ValueError, KeyError) as unit_err:
                    # Fall back to default unit for this variable
                    hourly_units[var_name] = default_unit
                    logger.warning(
                        f"Unknown unit for {var_name} (enum={variable.Unit()}), "
                        f"using default: {default_unit}"
                    )

        except Exception as e:
            logger.warning(f"Failed to extract variable {var_name}: {e}")

    # Infer model run time
    model_run_utc = infer_model_run_time(times_utc)

    return Forecast(
        lat=requested_lat,
        lon=requested_lon,
        api_lat=api_lat,
        api_lon=api_lon,
        elevation_m=elevation,
        model_id=model_id,
        model_run_utc=model_run_utc,
        times_utc=times_utc,
        hourly_data=hourly_data,
        hourly_units=hourly_units,
    )


def _parse_json_response(
    response: dict[str, Any],
    requested_lat: float,
    requested_lon: float,
    model_id: str,
    elevation_override: float | None,
) -> Forecast:
    """Parse a raw JSON API response."""
    # Check for error
    if "error" in response and response["error"]:
        reason = response.get("reason", "Unknown error")
        raise ApiError(f"API error: {reason}")

    # Extract coordinates
    api_lat = response.get("latitude", requested_lat)
    api_lon = response.get("longitude", requested_lon)

    # Extract elevation
    elevation = elevation_override
    if elevation is None:
        elevation = response.get("elevation")

    # Extract hourly data
    hourly = response.get("hourly", {})
    hourly_units_raw = response.get("hourly_units", {})

    if not hourly:
        raise ApiError("No hourly data in response")

    # Parse timestamps
    time_strings = hourly.get("time", [])
    times_utc = []
    for ts in time_strings:
        if isinstance(ts, str):
            # Parse ISO format timestamp
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            times_utc.append(dt)
        elif isinstance(ts, (int, float)):
            # Unix timestamp
            times_utc.append(datetime.fromtimestamp(ts, tz=timezone.utc))

    # Extract variable data
    hourly_data: dict[str, tuple[float | None, ...]] = {}
    hourly_units: dict[str, str] = {}

    variable_names = [
        "temperature_2m",
        "wind_speed_10m",
        "wind_gusts_10m",
        "snowfall",
        "precipitation",
        "freezing_level_height",
    ]

    for var_name in variable_names:
        if var_name in hourly:
            values = hourly[var_name]
            # Convert to tuple, handling None values
            hourly_data[var_name] = tuple(
                None if v is None else float(v) for v in values
            )

            # Get unit
            if var_name in hourly_units_raw:
                unit_str = hourly_units_raw[var_name]
                hourly_units[var_name] = decode_openmeteo_unit(unit_str)

    # Infer model run time
    model_run_utc = infer_model_run_time(times_utc)

    return Forecast(
        lat=requested_lat,
        lon=requested_lon,
        api_lat=api_lat,
        api_lon=api_lon,
        elevation_m=elevation,
        model_id=model_id,
        model_run_utc=model_run_utc,
        times_utc=times_utc,
        hourly_data=hourly_data,
        hourly_units=hourly_units,
    )

