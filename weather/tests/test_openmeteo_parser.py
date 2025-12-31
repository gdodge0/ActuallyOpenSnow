"""Tests for Open-Meteo response parsing."""

import pytest
import numpy as np
from datetime import datetime, timezone

from weather.parsing.openmeteo_parser import parse_openmeteo_response
from weather.domain.forecast import Forecast
from weather.domain.errors import ApiError


# -----------------------------------------------------------------------------
# Mock classes for FlatBuffers response simulation
# -----------------------------------------------------------------------------


class MockFlatBuffersResponse:
    """Mock Open-Meteo response object (simulates openmeteo_requests response)."""

    def __init__(
        self,
        latitude: float = 43.5,
        longitude: float = -110.75,
        elevation: float = 3000.0,
        hourly: "MockHourly | None" = None,
    ):
        self._latitude = latitude
        self._longitude = longitude
        self._elevation = elevation
        self._hourly = hourly or MockHourly()

    def Latitude(self) -> float:
        return self._latitude

    def Longitude(self) -> float:
        return self._longitude

    def Elevation(self) -> float:
        return self._elevation

    def Hourly(self):
        return self._hourly


class MockHourly:
    """Mock hourly data from Open-Meteo FlatBuffers."""

    def __init__(
        self,
        time_start: int | None = None,
        time_end: int | None = None,
        interval: int = 3600,
        variables: dict | None = None,
    ):
        if time_start is None:
            time_start = int(datetime(2024, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        if time_end is None:
            time_end = int(datetime(2024, 1, 16, 0, tzinfo=timezone.utc).timestamp())

        self._time_start = time_start
        self._time_end = time_end
        self._interval = interval

        # Default variables: index -> (values_array, unit_enum)
        # Unit enums: 1=C, 8=kmh, 4=cm, 3=mm, 5=m
        if variables is None:
            hours = (time_end - time_start) // interval
            self._variables = {
                0: (np.array([-5.0 + i * 0.5 for i in range(hours)]), 1),  # temp, C
                1: (np.array([20.0 + i for i in range(hours)]), 8),  # wind, kmh
                2: (np.array([35.0 + i for i in range(hours)]), 8),  # gusts, kmh
                3: (np.array([0.5 for _ in range(hours)]), 4),  # snow, cm
                4: (np.array([1.0 for _ in range(hours)]), 3),  # precip, mm
                5: (np.array([2000.0 + i * 10 for i in range(hours)]), 5),  # freeze, m
            }
        else:
            self._variables = variables

    def Time(self) -> int:
        return self._time_start

    def TimeEnd(self) -> int:
        return self._time_end

    def Interval(self) -> int:
        return self._interval

    def Variables(self, index: int):
        if index in self._variables:
            values, unit = self._variables[index]
            return MockVariable(values, unit)
        return None


class MockVariable:
    """Mock variable from Open-Meteo FlatBuffers."""

    def __init__(self, values: np.ndarray, unit: int):
        self._values = values
        self._unit = unit

    def ValuesAsNumpy(self) -> np.ndarray:
        return self._values

    def Unit(self) -> int:
        return self._unit


class TestParseJsonResponse:
    """Tests for parsing JSON API responses."""

    def test_parses_basic_response(self):
        """Test parsing a basic JSON response."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "elevation": 3000,
            "hourly_units": {
                "time": "iso8601",
                "temperature_2m": "°C",
                "wind_speed_10m": "km/h",
                "wind_gusts_10m": "km/h",
                "snowfall": "cm",
                "precipitation": "mm",
                "freezing_level_height": "m",
            },
            "hourly": {
                "time": [
                    "2024-01-15T00:00",
                    "2024-01-15T01:00",
                    "2024-01-15T02:00",
                ],
                "temperature_2m": [-5.0, -4.5, -4.0],
                "wind_speed_10m": [20.0, 22.0, 25.0],
                "wind_gusts_10m": [35.0, 38.0, 42.0],
                "snowfall": [0.5, 0.8, 1.0],
                "precipitation": [1.0, 1.5, 2.0],
                "freezing_level_height": [2000, 2050, 2100],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert isinstance(forecast, Forecast)
        assert forecast.lat == 43.48
        assert forecast.lon == -110.76
        assert forecast.api_lat == 43.5
        assert forecast.api_lon == -110.75
        assert forecast.elevation_m == 3000
        assert forecast.model_id == "gfs"
        assert len(forecast.times_utc) == 3

    def test_parses_units(self):
        """Test that units are correctly parsed."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {
                "temperature_2m": "°C",
                "wind_speed_10m": "km/h",
            },
            "hourly": {
                "time": ["2024-01-15T00:00"],
                "temperature_2m": [-5.0],
                "wind_speed_10m": [20.0],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.hourly_units["temperature_2m"] == "C"
        assert forecast.hourly_units["wind_speed_10m"] == "kmh"

    def test_handles_none_values(self):
        """Test handling of None/null values in data."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {
                "temperature_2m": "°C",
            },
            "hourly": {
                "time": ["2024-01-15T00:00", "2024-01-15T01:00"],
                "temperature_2m": [-5.0, None],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.hourly_data["temperature_2m"][0] == -5.0
        assert forecast.hourly_data["temperature_2m"][1] is None

    def test_elevation_override(self):
        """Test that elevation override is applied."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "elevation": 2500,  # API elevation
            "hourly_units": {},
            "hourly": {
                "time": ["2024-01-15T00:00"],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
            elevation_override=3200,  # Override elevation
        )

        assert forecast.elevation_m == 3200

    def test_parses_iso8601_timestamps(self):
        """Test parsing of ISO 8601 timestamps."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {},
            "hourly": {
                "time": [
                    "2024-01-15T00:00",
                    "2024-01-15T01:00",
                ],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.times_utc[0] == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        assert forecast.times_utc[1] == datetime(2024, 1, 15, 1, 0, tzinfo=timezone.utc)


class TestParseErrors:
    """Tests for error handling in parsing."""

    def test_api_error_in_response(self):
        """Test that API errors in response are raised."""
        response = {
            "error": True,
            "reason": "Invalid coordinates",
        }

        with pytest.raises(ApiError) as exc_info:
            parse_openmeteo_response(
                response=response,
                requested_lat=999,  # Invalid
                requested_lon=999,
                model_id="gfs",
            )

        assert "Invalid coordinates" in str(exc_info.value)

    def test_empty_hourly_raises(self):
        """Test that empty hourly data raises ApiError."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {},
            "hourly": {},
        }

        with pytest.raises(ApiError):
            parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
            )

    def test_missing_hourly_raises(self):
        """Test that missing hourly section raises ApiError."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
        }

        with pytest.raises(ApiError):
            parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
            )


class TestModelRunInference:
    """Tests for model run time inference."""

    def test_infers_model_run_time(self):
        """Test that model run time is inferred from timestamps."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {},
            "hourly": {
                "time": [
                    "2024-01-15T06:00",  # 06Z run
                    "2024-01-15T07:00",
                ],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        # Should infer 06Z model run
        assert forecast.model_run_utc == datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc)

    def test_infers_00z_run(self):
        """Test inference of 00Z model run."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {},
            "hourly": {
                "time": ["2024-01-15T00:00"],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.model_run_utc == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)

    def test_infers_12z_run(self):
        """Test inference of 12Z model run."""
        response = {
            "latitude": 43.5,
            "longitude": -110.75,
            "hourly_units": {},
            "hourly": {
                "time": ["2024-01-15T12:00"],
            },
        }

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.model_run_utc == datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc)


class TestParseFlatBuffersResponse:
    """Tests for parsing FlatBuffers API responses (openmeteo_requests library)."""

    def test_parses_basic_flatbuffers_response(self):
        """Test parsing a basic FlatBuffers response."""
        response = MockFlatBuffersResponse()

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert isinstance(forecast, Forecast)
        assert forecast.lat == 43.48
        assert forecast.lon == -110.76
        assert forecast.api_lat == 43.5
        assert forecast.api_lon == -110.75
        assert forecast.elevation_m == 3000.0
        assert forecast.model_id == "gfs"

    def test_parses_hourly_times(self):
        """Test that hourly timestamps are correctly parsed."""
        response = MockFlatBuffersResponse()

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        # Should have 24 hours of data
        assert len(forecast.times_utc) == 24
        assert forecast.times_utc[0] == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        assert forecast.times_utc[1] == datetime(2024, 1, 15, 1, 0, tzinfo=timezone.utc)

    def test_parses_variable_data(self):
        """Test that variable data is correctly extracted."""
        response = MockFlatBuffersResponse()

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        # Check temperature data
        assert "temperature_2m" in forecast.hourly_data
        assert forecast.hourly_data["temperature_2m"][0] == -5.0

        # Check snowfall data
        assert "snowfall" in forecast.hourly_data
        assert forecast.hourly_data["snowfall"][0] == 0.5

    def test_parses_unit_enums(self):
        """Test that unit enums are correctly decoded."""
        response = MockFlatBuffersResponse()

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.hourly_units["temperature_2m"] == "C"
        assert forecast.hourly_units["wind_speed_10m"] == "kmh"
        assert forecast.hourly_units["snowfall"] == "cm"
        assert forecast.hourly_units["precipitation"] == "mm"
        assert forecast.hourly_units["freezing_level_height"] == "m"

    def test_respects_requested_hourly_order_for_units(self, caplog):
        """Ensure units stay aligned when hourly variable order changes."""
        hours = 3
        time_start = int(datetime(2024, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        time_end = time_start + hours * 3600

        # Insert an extra temperature variable before snowfall to mimic client-side order.
        requested_hourly = (
            "temperature_2m",
            "wind_speed_10m",
            "wind_gusts_10m",
            "apparent_temperature",  # extra temperature variable
            "snowfall",
            "precipitation",
            "freezing_level_height",
        )

        variables = {
            0: (np.array([-5.0, -4.5, -4.0]), 1),  # temperature_2m (C)
            1: (np.array([20.0, 21.0, 22.0]), 8),  # wind_speed_10m (kmh)
            2: (np.array([30.0, 31.0, 32.0]), 8),  # wind_gusts_10m (kmh)
            3: (np.array([12.0, 13.0, 14.0]), 2),  # apparent_temperature (F)
            4: (np.array([0.5, 0.7, 1.0]), 4),     # snowfall (cm)
            5: (np.array([1.0, 1.1, 1.2]), 3),     # precipitation (mm)
            6: (np.array([2000.0, 2005.0, 2010.0]), 5),  # freezing_level_height (m)
        }

        hourly = MockHourly(
            time_start=time_start,
            time_end=time_end,
            interval=3600,
            variables=variables,
        )
        response = MockFlatBuffersResponse(hourly=hourly)

        with caplog.at_level("WARNING"):
            forecast = parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
                hourly_variables=requested_hourly,
            )

        # Snowfall should use the cm unit and not inherit the Fahrenheit unit.
        assert forecast.hourly_units["snowfall"] == "cm"
        assert forecast.hourly_data["snowfall"][0] == 0.5
        assert forecast.hourly_units["apparent_temperature"] == "F"
        assert "Unit category mismatch for snowfall" not in caplog.text

    def test_elevation_override(self):
        """Test that elevation override is applied."""
        response = MockFlatBuffersResponse(elevation=2500.0)

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
            elevation_override=3200,
        )

        assert forecast.elevation_m == 3200

    def test_handles_nan_values(self):
        """Test that NaN values are converted to None."""
        time_start = int(datetime(2024, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        time_end = int(datetime(2024, 1, 15, 3, tzinfo=timezone.utc).timestamp())

        # Create array with NaN
        values_with_nan = np.array([1.0, np.nan, 3.0])

        hourly = MockHourly(
            time_start=time_start,
            time_end=time_end,
            variables={
                0: (values_with_nan, 1),  # temp with NaN
            },
        )
        response = MockFlatBuffersResponse(hourly=hourly)

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        # NaN should be converted to None
        assert forecast.hourly_data["temperature_2m"][0] == 1.0
        assert forecast.hourly_data["temperature_2m"][1] is None
        assert forecast.hourly_data["temperature_2m"][2] == 3.0

    def test_missing_hourly_raises_error(self):
        """Test that missing hourly data raises ApiError."""
        response = MockFlatBuffersResponse()
        response._hourly = None

        with pytest.raises(ApiError) as exc_info:
            parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
            )

        assert "hourly" in str(exc_info.value).lower()

    def test_missing_variable_skipped(self):
        """Test that missing variables are gracefully skipped."""
        time_start = int(datetime(2024, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        time_end = int(datetime(2024, 1, 15, 3, tzinfo=timezone.utc).timestamp())

        # Only provide temperature, skip others
        hourly = MockHourly(
            time_start=time_start,
            time_end=time_end,
            variables={
                0: (np.array([1.0, 2.0, 3.0]), 1),  # Only temperature
            },
        )
        response = MockFlatBuffersResponse(hourly=hourly)

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        # Should have temperature but not other variables
        assert "temperature_2m" in forecast.hourly_data
        assert "wind_speed_10m" not in forecast.hourly_data

    def test_infers_model_run_time(self):
        """Test that model run time is inferred from timestamps."""
        # 06Z run
        time_start = int(datetime(2024, 1, 15, 6, tzinfo=timezone.utc).timestamp())
        time_end = int(datetime(2024, 1, 15, 12, tzinfo=timezone.utc).timestamp())

        hourly = MockHourly(time_start=time_start, time_end=time_end, variables={})
        response = MockFlatBuffersResponse(hourly=hourly)

        forecast = parse_openmeteo_response(
            response=response,
            requested_lat=43.48,
            requested_lon=-110.76,
            model_id="gfs",
        )

        assert forecast.model_run_utc == datetime(2024, 1, 15, 6, 0, tzinfo=timezone.utc)


class TestUnknownResponseType:
    """Tests for handling unknown response types."""

    def test_unknown_type_raises_error(self):
        """Test that unknown response type raises ApiError."""
        response = "not a valid response"

        with pytest.raises(ApiError) as exc_info:
            parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
            )

        assert "Unknown response type" in str(exc_info.value)

    def test_list_type_raises_error(self):
        """Test that list response type raises ApiError."""
        response = [1, 2, 3]

        with pytest.raises(ApiError) as exc_info:
            parse_openmeteo_response(
                response=response,
                requested_lat=43.48,
                requested_lon=-110.76,
                model_id="gfs",
            )

        assert "Unknown response type" in str(exc_info.value)

