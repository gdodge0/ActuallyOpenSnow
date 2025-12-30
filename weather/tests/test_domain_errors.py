"""Tests for custom exception classes."""

import pytest
from weather.domain.errors import (
    WeatherError,
    ApiError,
    UnitError,
    ModelError,
    RangeError,
)


class TestWeatherError:
    """Tests for base WeatherError class."""

    def test_creation(self):
        """Test basic WeatherError creation."""
        error = WeatherError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_is_exception(self):
        """Test that WeatherError is an Exception."""
        error = WeatherError("test")
        assert isinstance(error, Exception)

    def test_can_be_raised(self):
        """Test that WeatherError can be raised and caught."""
        with pytest.raises(WeatherError):
            raise WeatherError("test error")


class TestApiError:
    """Tests for ApiError class."""

    def test_creation_message_only(self):
        """Test ApiError with message only."""
        error = ApiError("Connection failed")
        assert "Connection failed" in str(error)
        assert error.status_code is None
        assert error.response_body is None

    def test_creation_with_status_code(self):
        """Test ApiError with status code."""
        error = ApiError("Not found", status_code=404)
        assert error.status_code == 404
        assert "Not found" in str(error)
        assert "404" in str(error)

    def test_creation_with_response_body(self):
        """Test ApiError with response body."""
        error = ApiError(
            "Error",
            status_code=500,
            response_body='{"error": "Internal error"}',
        )
        assert error.response_body == '{"error": "Internal error"}'

    def test_str_without_status_code(self):
        """Test __str__ without status code."""
        error = ApiError("API error occurred")
        assert str(error) == "API error occurred"

    def test_str_with_status_code(self):
        """Test __str__ with status code."""
        error = ApiError("Not found", status_code=404)
        result = str(error)
        assert "Not found" in result
        assert "(status=404)" in result

    def test_inherits_from_weather_error(self):
        """Test that ApiError inherits from WeatherError."""
        error = ApiError("test")
        assert isinstance(error, WeatherError)
        assert isinstance(error, Exception)

    def test_can_catch_as_weather_error(self):
        """Test that ApiError can be caught as WeatherError."""
        with pytest.raises(WeatherError):
            raise ApiError("test")


class TestUnitError:
    """Tests for UnitError class."""

    def test_creation_message_only(self):
        """Test UnitError with message only."""
        error = UnitError("Unknown unit")
        assert str(error) == "Unknown unit"
        assert error.unit is None

    def test_creation_with_unit(self):
        """Test UnitError with unit specified."""
        error = UnitError("Invalid unit 'xyz'", unit="xyz")
        assert error.unit == "xyz"
        assert "Invalid unit" in str(error)

    def test_inherits_from_weather_error(self):
        """Test that UnitError inherits from WeatherError."""
        error = UnitError("test")
        assert isinstance(error, WeatherError)

    def test_unit_attribute_accessible(self):
        """Test that unit attribute is accessible."""
        error = UnitError("Bad unit", unit="invalid")

        try:
            raise error
        except UnitError as e:
            assert e.unit == "invalid"


class TestModelError:
    """Tests for ModelError class."""

    def test_creation_message_only(self):
        """Test ModelError with message only."""
        error = ModelError("Unknown model")
        assert str(error) == "Unknown model"
        assert error.model_id is None

    def test_creation_with_model_id(self):
        """Test ModelError with model_id specified."""
        error = ModelError("Invalid model 'fake'", model_id="fake")
        assert error.model_id == "fake"
        assert "Invalid model" in str(error)

    def test_inherits_from_weather_error(self):
        """Test that ModelError inherits from WeatherError."""
        error = ModelError("test")
        assert isinstance(error, WeatherError)

    def test_model_id_attribute_accessible(self):
        """Test that model_id attribute is accessible."""
        error = ModelError("Bad model", model_id="invalid_model")

        try:
            raise error
        except ModelError as e:
            assert e.model_id == "invalid_model"


class TestRangeError:
    """Tests for RangeError class."""

    def test_creation(self):
        """Test RangeError creation."""
        error = RangeError("Time range out of bounds")
        assert str(error) == "Time range out of bounds"

    def test_inherits_from_weather_error(self):
        """Test that RangeError inherits from WeatherError."""
        error = RangeError("test")
        assert isinstance(error, WeatherError)

    def test_can_be_raised(self):
        """Test that RangeError can be raised and caught."""
        with pytest.raises(RangeError):
            raise RangeError("Range invalid")

    def test_can_catch_as_weather_error(self):
        """Test that RangeError can be caught as WeatherError."""
        with pytest.raises(WeatherError):
            raise RangeError("test")


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catching behavior."""

    def test_all_errors_catchable_as_weather_error(self):
        """Test that all error types are catchable as WeatherError."""
        errors = [
            ApiError("api"),
            UnitError("unit"),
            ModelError("model"),
            RangeError("range"),
        ]

        for error in errors:
            with pytest.raises(WeatherError):
                raise error

    def test_specific_catch_over_general(self):
        """Test that specific exceptions can be caught specifically."""
        try:
            raise ApiError("api error", status_code=500)
        except ApiError as e:
            assert e.status_code == 500
        except WeatherError:
            pytest.fail("Should have caught ApiError specifically")

    def test_can_access_attributes_after_catch(self):
        """Test that attributes are accessible after catching."""
        try:
            raise ApiError("error", status_code=404, response_body="Not found")
        except ApiError as e:
            assert e.status_code == 404
            assert e.response_body == "Not found"

