"""Tests for MeteoClient with mocked HTTP responses."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from weather.clients.openmeteo import MeteoClient
from weather.domain.forecast import Forecast
from weather.domain.errors import ApiError, ModelError


class MockOpenMeteoResponse:
    """Mock Open-Meteo response object."""

    def __init__(
        self,
        latitude: float = 43.5,
        longitude: float = -110.75,
        elevation: float = 3000.0,
    ):
        self._latitude = latitude
        self._longitude = longitude
        self._elevation = elevation
        self._hourly = MockHourly()

    def Latitude(self) -> float:
        return self._latitude

    def Longitude(self) -> float:
        return self._longitude

    def Elevation(self) -> float:
        return self._elevation

    def Hourly(self):
        return self._hourly


class MockHourly:
    """Mock hourly data from Open-Meteo."""

    def __init__(self):
        import numpy as np

        self._time_start = int(datetime(2024, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        self._time_end = int(datetime(2024, 1, 16, 0, tzinfo=timezone.utc).timestamp())
        self._interval = 3600  # 1 hour

        # Sample data for each variable
        self._variables = {
            0: ("temperature_2m", np.array([-5.0 + i * 0.5 for i in range(24)]), 1),
            1: ("wind_speed_10m", np.array([20.0 + i for i in range(24)]), 8),
            2: ("wind_gusts_10m", np.array([35.0 + i for i in range(24)]), 8),
            3: ("snowfall", np.array([0.5 for _ in range(24)]), 4),
            4: ("precipitation", np.array([1.0 for _ in range(24)]), 3),
            5: ("freezing_level_height", np.array([2000.0 + i * 10 for i in range(24)]), 5),
        }

    def Time(self) -> int:
        return self._time_start

    def TimeEnd(self) -> int:
        return self._time_end

    def Interval(self) -> int:
        return self._interval

    def Variables(self, index: int):
        if index in self._variables:
            name, values, unit = self._variables[index]
            return MockVariable(values, unit)
        return None


class MockVariable:
    """Mock variable from Open-Meteo FlatBuffers."""

    def __init__(self, values, unit: int):
        self._values = values
        self._unit = unit

    def ValuesAsNumpy(self):
        return self._values

    def Unit(self) -> int:
        return self._unit


class TestMeteoClientInit:
    """Tests for MeteoClient initialization."""

    def test_default_initialization(self):
        """Test client initializes with default settings."""
        client = MeteoClient()

        assert client.config.cache_expire_after == 3600
        assert client.config.max_retries == 3
        assert client.config.backoff_factor == 0.5

    def test_custom_initialization(self):
        """Test client initializes with custom settings."""
        client = MeteoClient(
            cache_expire_after=7200,
            max_retries=5,
            backoff_factor=1.0,
        )

        assert client.config.cache_expire_after == 7200
        assert client.config.max_retries == 5
        assert client.config.backoff_factor == 1.0

    def test_custom_hourly_variables(self):
        """Test client with custom hourly variables."""
        variables = ("temperature_2m", "wind_speed_10m")
        client = MeteoClient(hourly_variables=variables)

        assert client.hourly_variables == variables


class TestGetForecast:
    """Tests for get_forecast method with mocked responses."""

    @patch.object(MeteoClient, "_setup_session")
    def test_get_forecast_success(self, mock_setup):
        """Test successful forecast retrieval."""
        client = MeteoClient()

        # Mock the client's weather_api method
        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        forecast = client.get_forecast(43.48, -110.76, model="gfs")

        assert isinstance(forecast, Forecast)
        assert forecast.lat == 43.48
        assert forecast.lon == -110.76
        assert forecast.api_lat == 43.5
        assert forecast.api_lon == -110.75
        assert forecast.model_id == "gfs"

    @patch.object(MeteoClient, "_setup_session")
    def test_get_forecast_with_elevation(self, mock_setup):
        """Test forecast with elevation override."""
        client = MeteoClient()

        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        forecast = client.get_forecast(
            43.48,
            -110.76,
            model="gfs",
            elevation=3200,
        )

        assert forecast.elevation_m == 3200

    @patch.object(MeteoClient, "_setup_session")
    def test_get_forecast_invalid_model(self, mock_setup):
        """Test that invalid model raises ModelError."""
        client = MeteoClient()

        with pytest.raises(ModelError):
            client.get_forecast(43.48, -110.76, model="invalid_model")

    @patch.object(MeteoClient, "_setup_session")
    def test_get_forecast_api_error(self, mock_setup):
        """Test that API errors are properly raised."""
        client = MeteoClient()

        client._client = Mock()
        client._client.weather_api.side_effect = Exception("Connection failed")

        with pytest.raises(ApiError) as exc_info:
            client.get_forecast(43.48, -110.76)

        assert "Connection failed" in str(exc_info.value)

    @patch.object(MeteoClient, "_setup_session")
    def test_get_forecast_empty_response(self, mock_setup):
        """Test that empty response raises ApiError."""
        client = MeteoClient()

        client._client = Mock()
        client._client.weather_api.return_value = []

        with pytest.raises(ApiError) as exc_info:
            client.get_forecast(43.48, -110.76)

        assert "Empty response" in str(exc_info.value)


class TestModelSelection:
    """Tests for model selection and validation."""

    @patch.object(MeteoClient, "_setup_session")
    def test_gfs_model(self, mock_setup):
        """Test GFS model selection."""
        client = MeteoClient()

        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        forecast = client.get_forecast(43.48, -110.76, model="gfs")
        assert forecast.model_id == "gfs"

    @patch.object(MeteoClient, "_setup_session")
    def test_ifs_model(self, mock_setup):
        """Test IFS model selection."""
        client = MeteoClient()

        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        forecast = client.get_forecast(43.48, -110.76, model="ifs")
        assert forecast.model_id == "ifs"

    @patch.object(MeteoClient, "_setup_session")
    def test_aifs_model(self, mock_setup):
        """Test AIFS model selection."""
        client = MeteoClient()

        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        forecast = client.get_forecast(43.48, -110.76, model="aifs")
        assert forecast.model_id == "aifs"

    @patch.object(MeteoClient, "_setup_session")
    def test_model_alias(self, mock_setup):
        """Test model aliases work."""
        client = MeteoClient()

        mock_response = MockOpenMeteoResponse()
        client._client = Mock()
        client._client.weather_api.return_value = [mock_response]

        # "ecmwf" is an alias for "ifs"
        forecast = client.get_forecast(43.48, -110.76, model="ecmwf")
        assert forecast.model_id == "ifs"


class TestBuildParams:
    """Tests for _build_params method."""

    @patch.object(MeteoClient, "_setup_session")
    def test_basic_params(self, mock_setup):
        """Test basic parameter building."""
        from weather.config.models import get_model_config

        client = MeteoClient()
        model_config = get_model_config("gfs")

        params = client._build_params(
            lat=43.48,
            lon=-110.76,
            model_config=model_config,
            elevation=None,
            temperature_unit="celsius",
            wind_speed_unit="kmh",
            precipitation_unit="mm",
        )

        assert params["latitude"] == 43.48
        assert params["longitude"] == -110.76
        assert params["models"] == "gfs_seamless"
        assert params["timezone"] == "UTC"
        assert "hourly" in params

    @patch.object(MeteoClient, "_setup_session")
    def test_elevation_param(self, mock_setup):
        """Test elevation parameter is included when specified."""
        from weather.config.models import get_model_config

        client = MeteoClient()
        model_config = get_model_config("gfs")

        params = client._build_params(
            lat=43.48,
            lon=-110.76,
            model_config=model_config,
            elevation=3200,
            temperature_unit="celsius",
            wind_speed_unit="kmh",
            precipitation_unit="mm",
        )

        assert params["elevation"] == 3200

    @patch.object(MeteoClient, "_setup_session")
    def test_unit_preferences(self, mock_setup):
        """Test unit preferences are included."""
        from weather.config.models import get_model_config

        client = MeteoClient()
        model_config = get_model_config("gfs")

        params = client._build_params(
            lat=43.48,
            lon=-110.76,
            model_config=model_config,
            elevation=None,
            temperature_unit="fahrenheit",
            wind_speed_unit="mph",
            precipitation_unit="inch",
        )

        assert params["temperature_unit"] == "fahrenheit"
        assert params["wind_speed_unit"] == "mph"
        assert params["precipitation_unit"] == "inch"

