"""Tests for unit normalization."""

import pytest
from weather.units.normalize import normalize_unit, get_unit_category, CANONICAL_UNITS
from weather.domain.errors import UnitError


class TestNormalizeUnit:
    """Tests for normalize_unit function."""

    def test_canonical_units_return_unchanged(self):
        """Test that canonical units are returned as-is."""
        for unit in CANONICAL_UNITS:
            assert normalize_unit(unit) == unit

    def test_temperature_aliases(self):
        """Test temperature unit aliases."""
        assert normalize_unit("celsius") == "C"
        assert normalize_unit("°C") == "C"
        assert normalize_unit("°c") == "C"
        assert normalize_unit("fahrenheit") == "F"
        assert normalize_unit("°F") == "F"
        assert normalize_unit("°f") == "F"
        assert normalize_unit("kelvin") == "K"

    def test_speed_aliases(self):
        """Test speed unit aliases."""
        assert normalize_unit("km/h") == "kmh"
        assert normalize_unit("kmph") == "kmh"
        assert normalize_unit("kph") == "kmh"
        assert normalize_unit("m/s") == "ms"
        assert normalize_unit("mps") == "ms"
        assert normalize_unit("mi/h") == "mph"
        assert normalize_unit("knots") == "kn"
        assert normalize_unit("kt") == "kn"

    def test_length_aliases(self):
        """Test length unit aliases."""
        assert normalize_unit("millimeter") == "mm"
        assert normalize_unit("millimeters") == "mm"
        assert normalize_unit("centimeter") == "cm"
        assert normalize_unit("centimeters") == "cm"
        assert normalize_unit("meter") == "m"
        assert normalize_unit("meters") == "m"
        assert normalize_unit("metre") == "m"
        assert normalize_unit("metres") == "m"
        assert normalize_unit("inch") == "in"
        assert normalize_unit("inches") == "in"
        assert normalize_unit("foot") == "ft"
        assert normalize_unit("feet") == "ft"

    def test_pressure_aliases(self):
        """Test pressure unit aliases."""
        assert normalize_unit("hpa") == "hPa"
        assert normalize_unit("mbar") == "hPa"
        assert normalize_unit("mb") == "hPa"

    def test_percentage_aliases(self):
        """Test percentage aliases."""
        assert normalize_unit("percent") == "%"
        assert normalize_unit("pct") == "%"

    def test_case_insensitive(self):
        """Test that aliases are case-insensitive."""
        assert normalize_unit("CELSIUS") == "C"
        assert normalize_unit("Fahrenheit") == "F"
        assert normalize_unit("KM/H") == "kmh"

    def test_unknown_unit_raises(self):
        """Test that unknown units raise UnitError."""
        with pytest.raises(UnitError) as exc_info:
            normalize_unit("unknown_unit")
        assert exc_info.value.unit == "unknown_unit"


class TestGetUnitCategory:
    """Tests for get_unit_category function."""

    def test_temperature_category(self):
        """Test temperature units are categorized correctly."""
        assert get_unit_category("C") == "temperature"
        assert get_unit_category("F") == "temperature"
        assert get_unit_category("K") == "temperature"
        assert get_unit_category("celsius") == "temperature"

    def test_speed_category(self):
        """Test speed units are categorized correctly."""
        assert get_unit_category("kmh") == "speed"
        assert get_unit_category("ms") == "speed"
        assert get_unit_category("mph") == "speed"
        assert get_unit_category("kn") == "speed"
        assert get_unit_category("km/h") == "speed"

    def test_length_category(self):
        """Test length units are categorized correctly."""
        assert get_unit_category("mm") == "length"
        assert get_unit_category("cm") == "length"
        assert get_unit_category("m") == "length"
        assert get_unit_category("in") == "length"
        assert get_unit_category("ft") == "length"

    def test_percentage_category(self):
        """Test percentage is categorized correctly."""
        assert get_unit_category("%") == "percentage"

    def test_pressure_category(self):
        """Test pressure units are categorized correctly."""
        assert get_unit_category("hPa") == "pressure"

    def test_other_category(self):
        """Test other units are categorized correctly."""
        assert get_unit_category("W/m²") == "other"
        assert get_unit_category("°") == "other"

