"""Tests for unit conversion functions."""

import pytest
from weather.units.convert import (
    convert_temperature,
    convert_speed,
    convert_length,
    convert_value,
    convert_series,
)
from weather.domain.quantities import Series
from weather.domain.errors import UnitError


class TestConvertTemperature:
    """Tests for temperature conversion."""

    def test_celsius_to_fahrenheit(self):
        """Test C to F conversion."""
        assert convert_temperature(0, "C", "F") == 32
        assert convert_temperature(100, "C", "F") == 212
        assert convert_temperature(-40, "C", "F") == -40  # Same in both!

    def test_fahrenheit_to_celsius(self):
        """Test F to C conversion."""
        assert convert_temperature(32, "F", "C") == 0
        assert convert_temperature(212, "F", "C") == 100
        assert convert_temperature(-40, "F", "C") == -40

    def test_celsius_to_kelvin(self):
        """Test C to K conversion."""
        assert convert_temperature(0, "C", "K") == 273.15
        assert convert_temperature(-273.15, "C", "K") == 0

    def test_kelvin_to_celsius(self):
        """Test K to C conversion."""
        assert convert_temperature(273.15, "K", "C") == 0
        assert convert_temperature(0, "K", "C") == -273.15

    def test_fahrenheit_to_kelvin(self):
        """Test F to K conversion."""
        result = convert_temperature(32, "F", "K")
        assert abs(result - 273.15) < 0.01

    def test_same_unit_returns_value(self):
        """Test that same unit returns the same value."""
        assert convert_temperature(25, "C", "C") == 25
        assert convert_temperature(77, "F", "F") == 77
        assert convert_temperature(300, "K", "K") == 300

    def test_accepts_aliases(self):
        """Test that unit aliases work."""
        assert convert_temperature(0, "celsius", "fahrenheit") == 32
        assert convert_temperature(32, "°F", "°C") == 0

    def test_invalid_unit_raises(self):
        """Test that invalid units raise UnitError."""
        with pytest.raises(UnitError):
            convert_temperature(25, "C", "mph")


class TestConvertSpeed:
    """Tests for speed conversion."""

    def test_kmh_to_mph(self):
        """Test km/h to mph conversion."""
        result = convert_speed(100, "kmh", "mph")
        assert abs(result - 62.137) < 0.01

    def test_mph_to_kmh(self):
        """Test mph to km/h conversion."""
        result = convert_speed(60, "mph", "kmh")
        assert abs(result - 96.56) < 0.01

    def test_ms_to_kmh(self):
        """Test m/s to km/h conversion."""
        assert abs(convert_speed(1, "ms", "kmh") - 3.6) < 0.0001

    def test_kmh_to_ms(self):
        """Test km/h to m/s conversion."""
        result = convert_speed(36, "kmh", "ms")
        assert abs(result - 10) < 0.01

    def test_knots_to_mph(self):
        """Test knots to mph conversion."""
        result = convert_speed(100, "kn", "mph")
        assert abs(result - 115.08) < 0.1

    def test_mph_to_knots(self):
        """Test mph to knots conversion."""
        result = convert_speed(115.08, "mph", "kn")
        assert abs(result - 100) < 0.1

    def test_same_unit_returns_value(self):
        """Test that same unit returns the same value."""
        assert convert_speed(50, "kmh", "kmh") == 50

    def test_accepts_aliases(self):
        """Test that unit aliases work."""
        result = convert_speed(100, "km/h", "m/s")
        assert abs(result - 27.78) < 0.01


class TestConvertLength:
    """Tests for length conversion."""

    def test_mm_to_inches(self):
        """Test mm to inches conversion."""
        result = convert_length(25.4, "mm", "in")
        assert abs(result - 1) < 0.001

    def test_inches_to_mm(self):
        """Test inches to mm conversion."""
        result = convert_length(1, "in", "mm")
        assert abs(result - 25.4) < 0.01

    def test_cm_to_inches(self):
        """Test cm to inches conversion."""
        result = convert_length(2.54, "cm", "in")
        assert abs(result - 1) < 0.001

    def test_meters_to_feet(self):
        """Test meters to feet conversion."""
        result = convert_length(1, "m", "ft")
        assert abs(result - 3.281) < 0.01

    def test_feet_to_meters(self):
        """Test feet to meters conversion."""
        result = convert_length(3.281, "ft", "m")
        assert abs(result - 1) < 0.01

    def test_mm_to_cm(self):
        """Test mm to cm conversion."""
        assert convert_length(10, "mm", "cm") == 1

    def test_cm_to_mm(self):
        """Test cm to mm conversion."""
        assert convert_length(1, "cm", "mm") == 10

    def test_same_unit_returns_value(self):
        """Test that same unit returns the same value."""
        assert convert_length(100, "mm", "mm") == 100


class TestConvertValue:
    """Tests for auto-detecting conversion."""

    def test_auto_detects_temperature(self):
        """Test that temperature units are auto-detected."""
        assert convert_value(0, "C", "F") == 32

    def test_auto_detects_speed(self):
        """Test that speed units are auto-detected."""
        result = convert_value(100, "kmh", "mph")
        assert abs(result - 62.137) < 0.01

    def test_auto_detects_length(self):
        """Test that length units are auto-detected."""
        result = convert_value(25.4, "mm", "in")
        assert abs(result - 1) < 0.001

    def test_incompatible_units_raises(self):
        """Test that incompatible units raise UnitError."""
        with pytest.raises(UnitError):
            convert_value(25, "C", "mm")


class TestConvertSeries:
    """Tests for series conversion."""

    def test_converts_all_values(self):
        """Test that all values in a series are converted."""
        series = Series(values=(0.0, 10.0, 20.0, 30.0), unit="C")
        result = convert_series(series, "F")

        assert result.unit == "F"
        assert len(result.values) == 4
        assert result.values[0] == 32.0
        assert abs(result.values[1] - 50.0) < 0.01
        assert abs(result.values[2] - 68.0) < 0.01
        assert abs(result.values[3] - 86.0) < 0.01

    def test_handles_none_values(self):
        """Test that None values are preserved."""
        series = Series(values=(0.0, None, 20.0, None), unit="C")
        result = convert_series(series, "F")

        assert result.values[0] == 32.0
        assert result.values[1] is None
        assert abs(result.values[2] - 68.0) < 0.01
        assert result.values[3] is None

    def test_same_unit_returns_original(self):
        """Test that same unit conversion returns the series."""
        series = Series(values=(1.0, 2.0, 3.0), unit="mm")
        result = convert_series(series, "mm")

        assert result.unit == "mm"
        assert result.values == series.values

