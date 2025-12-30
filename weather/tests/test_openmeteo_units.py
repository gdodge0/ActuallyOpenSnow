"""Tests for Open-Meteo unit decoding functions."""

import pytest
from weather.units.openmeteo_units import (
    decode_openmeteo_unit,
    get_default_unit,
    OPENMETEO_UNIT_MAP,
    FLATBUFFERS_UNIT_ENUM,
)


class TestDecodeOpenmeteoUnitStrings:
    """Tests for decode_openmeteo_unit with string inputs (JSON API)."""

    def test_temperature_units(self):
        """Test decoding temperature unit strings."""
        assert decode_openmeteo_unit("°C") == "C"
        assert decode_openmeteo_unit("°F") == "F"

    def test_speed_units(self):
        """Test decoding speed unit strings."""
        assert decode_openmeteo_unit("km/h") == "kmh"
        assert decode_openmeteo_unit("m/s") == "ms"
        assert decode_openmeteo_unit("mph") == "mph"
        assert decode_openmeteo_unit("kn") == "kn"
        assert decode_openmeteo_unit("knots") == "kn"

    def test_length_units(self):
        """Test decoding length/precipitation unit strings."""
        assert decode_openmeteo_unit("mm") == "mm"
        assert decode_openmeteo_unit("cm") == "cm"
        assert decode_openmeteo_unit("m") == "m"
        assert decode_openmeteo_unit("inch") == "in"
        assert decode_openmeteo_unit("in") == "in"
        assert decode_openmeteo_unit("ft") == "ft"

    def test_pressure_units(self):
        """Test decoding pressure unit strings."""
        assert decode_openmeteo_unit("hPa") == "hPa"

    def test_percentage_units(self):
        """Test decoding percentage unit strings."""
        assert decode_openmeteo_unit("%") == "%"

    def test_other_units(self):
        """Test decoding other unit strings."""
        assert decode_openmeteo_unit("W/m²") == "W/m²"
        assert decode_openmeteo_unit("°") == "°"

    def test_time_units_passthrough(self):
        """Test that time format strings pass through."""
        assert decode_openmeteo_unit("iso8601") == "iso8601"
        assert decode_openmeteo_unit("unixtime") == "unixtime"

    def test_unknown_string_tries_normalize(self):
        """Test that unknown strings attempt normalization."""
        # "celsius" is not in OPENMETEO_UNIT_MAP but normalize_unit handles it
        assert decode_openmeteo_unit("celsius") == "C"
        assert decode_openmeteo_unit("fahrenheit") == "F"

    def test_unknown_string_raises(self):
        """Test that truly unknown strings raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            decode_openmeteo_unit("invalid_unit_xyz")

        assert "Unknown" in str(exc_info.value)


class TestDecodeOpenmeteoUnitIntegers:
    """Tests for decode_openmeteo_unit with integer inputs (FlatBuffers)."""

    def test_undefined_unit(self):
        """Test decoding undefined unit (enum 0)."""
        assert decode_openmeteo_unit(0) == "undefined"

    def test_temperature_units(self):
        """Test decoding temperature unit enums."""
        assert decode_openmeteo_unit(1) == "C"
        assert decode_openmeteo_unit(2) == "F"

    def test_length_units(self):
        """Test decoding length unit enums."""
        assert decode_openmeteo_unit(3) == "mm"
        assert decode_openmeteo_unit(4) == "cm"
        assert decode_openmeteo_unit(5) == "m"
        assert decode_openmeteo_unit(6) == "in"
        assert decode_openmeteo_unit(7) == "ft"

    def test_speed_units(self):
        """Test decoding speed unit enums."""
        assert decode_openmeteo_unit(8) == "kmh"
        assert decode_openmeteo_unit(9) == "ms"
        assert decode_openmeteo_unit(10) == "mph"
        assert decode_openmeteo_unit(11) == "kn"

    def test_percentage_unit(self):
        """Test decoding percentage unit enum."""
        assert decode_openmeteo_unit(12) == "%"

    def test_pressure_unit(self):
        """Test decoding pressure unit enum."""
        assert decode_openmeteo_unit(13) == "hPa"

    def test_radiation_unit(self):
        """Test decoding radiation unit enum."""
        assert decode_openmeteo_unit(14) == "W/m²"

    def test_degree_unit(self):
        """Test decoding degree unit enum (for wind direction)."""
        assert decode_openmeteo_unit(15) == "°"

    def test_kelvin_unit(self):
        """Test decoding Kelvin unit enum."""
        assert decode_openmeteo_unit(22) == "K"

    def test_unknown_enum_raises(self):
        """Test that unknown enum values raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            decode_openmeteo_unit(999)

        assert "Unknown FlatBuffers unit enum" in str(exc_info.value)

    def test_all_defined_enums_decode(self):
        """Test that all defined enum values can be decoded."""
        for enum_val in FLATBUFFERS_UNIT_ENUM:
            # Should not raise
            result = decode_openmeteo_unit(enum_val)
            assert isinstance(result, str)


class TestGetDefaultUnit:
    """Tests for get_default_unit function."""

    def test_temperature_variables(self):
        """Test default units for temperature variables."""
        assert get_default_unit("temperature_2m") == "C"
        assert get_default_unit("apparent_temperature") == "C"
        assert get_default_unit("dew_point_2m") == "C"

    def test_wind_variables(self):
        """Test default units for wind variables."""
        assert get_default_unit("wind_speed_10m") == "kmh"
        assert get_default_unit("wind_speed_80m") == "kmh"
        assert get_default_unit("wind_speed_120m") == "kmh"
        assert get_default_unit("wind_gusts_10m") == "kmh"
        assert get_default_unit("wind_direction_10m") == "°"

    def test_precipitation_variables(self):
        """Test default units for precipitation variables."""
        assert get_default_unit("precipitation") == "mm"
        assert get_default_unit("rain") == "mm"
        assert get_default_unit("showers") == "mm"
        assert get_default_unit("snowfall") == "cm"
        assert get_default_unit("snow_depth") == "m"

    def test_height_variables(self):
        """Test default units for height variables."""
        assert get_default_unit("freezing_level_height") == "m"
        assert get_default_unit("visibility") == "m"

    def test_percentage_variables(self):
        """Test default units for percentage variables."""
        assert get_default_unit("relative_humidity_2m") == "%"
        assert get_default_unit("cloud_cover") == "%"

    def test_pressure_variables(self):
        """Test default units for pressure variables."""
        assert get_default_unit("surface_pressure") == "hPa"

    def test_radiation_variables(self):
        """Test default units for radiation variables."""
        assert get_default_unit("shortwave_radiation") == "W/m²"

    def test_unknown_variable_returns_undefined(self):
        """Test that unknown variables return 'undefined'."""
        assert get_default_unit("unknown_variable") == "undefined"
        assert get_default_unit("made_up_var") == "undefined"


class TestUnitMapCompleteness:
    """Tests for completeness of unit mappings."""

    def test_all_openmeteo_strings_normalized(self):
        """Test that all OPENMETEO_UNIT_MAP values normalize correctly."""
        from weather.units.normalize import normalize_unit, CANONICAL_UNITS

        for api_string, canonical in OPENMETEO_UNIT_MAP.items():
            if canonical in ("iso8601", "unixtime"):
                continue  # These are pass-through values
            # Should be in canonical units or normalizable
            try:
                result = normalize_unit(canonical)
                assert isinstance(result, str)
            except Exception:
                # If not normalizable, should be in canonical units
                assert canonical in CANONICAL_UNITS or canonical in (
                    "W/m²",
                    "°",
                    "J/kg",
                    "μg/m³",
                    "grains/m³",
                    "undefined",
                )

