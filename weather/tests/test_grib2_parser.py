"""Tests for GRIB2 parser utilities."""

import pytest
from weather.parsing.grib2_parser import (
    de_accumulate,
    compute_wind_speed,
    estimate_wind_gusts,
    build_hourly_data,
)


class TestDeAccumulate:
    """Tests for de-accumulation of GRIB2 accumulated fields."""

    def test_empty_input(self):
        assert de_accumulate([]) == []

    def test_single_value(self):
        assert de_accumulate([5.0]) == [5.0]

    def test_monotonically_increasing(self):
        """Standard accumulation: 0, 1, 3, 6 → 0, 1, 2, 3."""
        result = de_accumulate([0.0, 1.0, 3.0, 6.0])
        assert result == [0.0, 1.0, 2.0, 3.0]

    def test_none_values_preserved(self):
        result = de_accumulate([1.0, None, 5.0])
        assert result[0] == 1.0
        assert result[1] is None
        assert result[2] == pytest.approx(4.0)

    def test_negative_increment_clamped_to_zero(self):
        """Floating-point errors can cause tiny negative increments."""
        result = de_accumulate([1.0, 0.999])
        assert result[1] == 0.0

    def test_all_zeros(self):
        result = de_accumulate([0.0, 0.0, 0.0])
        assert result == [0.0, 0.0, 0.0]

    def test_large_accumulation(self):
        result = de_accumulate([10.0, 25.0, 50.0, 100.0])
        assert result == [10.0, 15.0, 25.0, 50.0]

    def test_first_value_negative_clamped(self):
        """First value should be clamped to 0 if negative."""
        result = de_accumulate([-0.001, 1.0])
        assert result[0] == 0.0
        assert result[1] == pytest.approx(1.001)

    def test_all_none(self):
        result = de_accumulate([None, None, None])
        assert result == [None, None, None]


class TestComputeWindSpeed:
    """Tests for wind speed computation from U/V components."""

    def test_zero_wind(self):
        result = compute_wind_speed([0.0], [0.0])
        assert result == [0.0]

    def test_pure_east_wind(self):
        """10 m/s east wind → 36 km/h."""
        result = compute_wind_speed([10.0], [0.0])
        assert result[0] == pytest.approx(36.0)

    def test_pure_north_wind(self):
        result = compute_wind_speed([0.0], [10.0])
        assert result[0] == pytest.approx(36.0)

    def test_diagonal_wind(self):
        """sqrt(3^2 + 4^2) = 5 m/s → 18 km/h."""
        result = compute_wind_speed([3.0], [4.0])
        assert result[0] == pytest.approx(18.0)

    def test_none_values(self):
        result = compute_wind_speed([None, 5.0], [3.0, None])
        assert result[0] is None
        assert result[1] is None

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            compute_wind_speed([1.0, 2.0], [1.0])

    def test_multiple_values(self):
        result = compute_wind_speed([0.0, 10.0, 3.0], [0.0, 0.0, 4.0])
        assert result[0] == 0.0
        assert result[1] == pytest.approx(36.0)
        assert result[2] == pytest.approx(18.0)


class TestEstimateWindGusts:
    """Tests for wind gust estimation."""

    def test_with_direct_gust_values(self):
        """When gust values are provided, use them directly."""
        speed = [10.0, 20.0]
        gusts = [15.0, 30.0]
        result = estimate_wind_gusts(speed, gusts)
        assert result == [15.0, 30.0]

    def test_estimate_from_speed(self):
        """Without gust data, estimate as 1.5x wind speed."""
        speed = [10.0, 20.0, 0.0]
        result = estimate_wind_gusts(speed)
        assert result == [15.0, 30.0, 0.0]

    def test_custom_gust_factor(self):
        speed = [10.0]
        result = estimate_wind_gusts(speed, gust_factor=2.0)
        assert result == [20.0]

    def test_none_speed_values(self):
        speed = [None, 10.0]
        result = estimate_wind_gusts(speed)
        assert result[0] is None
        assert result[1] == 15.0

    def test_mismatched_gust_length_falls_back(self):
        """If gust array length doesn't match, estimate instead."""
        speed = [10.0, 20.0]
        gusts = [15.0]  # Wrong length
        result = estimate_wind_gusts(speed, gusts)
        assert result == [15.0, 30.0]


class TestBuildHourlyData:
    """Tests for building Forecast-compatible hourly data from GRIB2 extracts."""

    def _make_point(
        self,
        temp_k=280.0,
        precip=0.0,
        snow=0.0,
        u=0.0,
        v=0.0,
        gusts=None,
        freezing=3000.0,
    ):
        return {
            "temperature": temp_k,
            "precipitation": precip,
            "snowfall": snow,
            "wind_u": u,
            "wind_v": v,
            "wind_gusts": gusts,
            "freezing_level": freezing,
        }

    def test_empty_input(self):
        data, units = build_hourly_data([], "gfs")
        assert data == {}
        assert units == {}

    def test_single_hour(self):
        points = [self._make_point(temp_k=273.15)]
        data, units = build_hourly_data(points, "gfs")
        assert "temperature_2m" in data
        assert data["temperature_2m"][0] == pytest.approx(0.0)
        assert units["temperature_2m"] == "C"

    def test_temperature_kelvin_to_celsius(self):
        """Temperature should be converted from K to C."""
        points = [self._make_point(temp_k=300.0)]
        data, _ = build_hourly_data(points, "gfs")
        assert data["temperature_2m"][0] == pytest.approx(26.85)

    def test_snowfall_meters_to_cm(self):
        """Snowfall should be converted from meters to cm."""
        points = [
            self._make_point(snow=0.0),
            self._make_point(snow=0.05),  # 5cm accumulated
        ]
        data, _ = build_hourly_data(points, "gfs")
        # De-accumulated and converted: first hour = 0, second = 0.05m = 5cm
        assert data["snowfall"][0] == pytest.approx(0.0)
        assert data["snowfall"][1] == pytest.approx(5.0)

    def test_precipitation_de_accumulated(self):
        points = [
            self._make_point(precip=0.0),
            self._make_point(precip=2.0),
            self._make_point(precip=5.0),
        ]
        data, _ = build_hourly_data(points, "gfs")
        assert data["precipitation"] == pytest.approx((0.0, 2.0, 3.0))

    def test_wind_speed_from_uv(self):
        """Wind speed should be computed from U/V and converted to km/h."""
        points = [self._make_point(u=3.0, v=4.0)]
        data, _ = build_hourly_data(points, "gfs")
        assert data["wind_speed_10m"][0] == pytest.approx(18.0)

    def test_ecmwf_gust_estimation(self):
        """ECMWF models should estimate gusts as 1.5x wind speed when no gust data."""
        points = [self._make_point(u=10.0, v=0.0, gusts=None)]
        data, _ = build_hourly_data(points, "ifs")
        wind_speed = data["wind_speed_10m"][0]
        assert data["wind_gusts_10m"][0] == pytest.approx(wind_speed * 1.5)

    def test_non_ecmwf_direct_gusts(self):
        """Non-ECMWF models should use direct gust values converted to km/h."""
        points = [self._make_point(u=0.0, v=0.0, gusts=15.0)]
        data, _ = build_hourly_data(points, "gfs")
        # 15 m/s → 54 km/h
        assert data["wind_gusts_10m"][0] == pytest.approx(54.0)

    def test_all_units_present(self):
        points = [self._make_point()]
        _, units = build_hourly_data(points, "gfs")
        assert units["temperature_2m"] == "C"
        assert units["wind_speed_10m"] == "kmh"
        assert units["wind_gusts_10m"] == "kmh"
        assert units["snowfall"] == "cm"
        assert units["precipitation"] == "mm"
        assert units["freezing_level_height"] == "m"

    def test_none_temperature(self):
        points = [self._make_point(temp_k=None)]
        data, _ = build_hourly_data(points, "gfs")
        assert data["temperature_2m"][0] is None

    def test_multiple_hours_full_pipeline(self):
        """Test full pipeline with 3 hours of data."""
        points = [
            self._make_point(temp_k=268.15, precip=0.0, snow=0.0, u=5.0, v=5.0),
            self._make_point(temp_k=267.15, precip=2.0, snow=0.02, u=8.0, v=6.0),
            self._make_point(temp_k=266.15, precip=6.0, snow=0.07, u=3.0, v=4.0),
        ]
        data, units = build_hourly_data(points, "gfs")

        # Temperatures: 268.15-273.15=-5, 267.15-273.15=-6, 266.15-273.15=-7
        assert data["temperature_2m"][0] == pytest.approx(-5.0)
        assert data["temperature_2m"][1] == pytest.approx(-6.0)
        assert data["temperature_2m"][2] == pytest.approx(-7.0)

        # Precipitation: de-accumulated from 0, 2, 6 → 0, 2, 4
        assert data["precipitation"] == pytest.approx((0.0, 2.0, 4.0))

        # Snowfall: de-accumulated from 0, 0.02, 0.07 → 0, 0.02, 0.05 meters
        # Then ×100 for cm: 0, 2, 5
        assert data["snowfall"] == pytest.approx((0.0, 2.0, 5.0))

        assert len(data["wind_speed_10m"]) == 3
        assert all(v is not None for v in data["wind_speed_10m"])


class TestEcmwfUnitConversion:
    """Tests for ECMWF precipitation/snowfall unit conversion (m → mm)."""

    def _make_point(
        self,
        temp_k=280.0,
        precip=0.0,
        snow=0.0,
        u=0.0,
        v=0.0,
        gusts=None,
        freezing=3000.0,
    ):
        return {
            "temperature": temp_k,
            "precipitation": precip,
            "snowfall": snow,
            "wind_u": u,
            "wind_v": v,
            "wind_gusts": gusts,
            "freezing_level": freezing,
        }

    def test_ecmwf_precipitation_converted_from_meters(self):
        """ECMWF tp is in meters; should be ×1000 before de-accumulation."""
        # 0.002 m accumulated → 2 mm after ×1000
        points = [
            self._make_point(precip=0.0),
            self._make_point(precip=0.002),  # 0.002 m = 2 mm
        ]
        data, _ = build_hourly_data(points, "ifs")
        # De-accumulated: [0, 2.0] mm
        assert data["precipitation"][0] == pytest.approx(0.0)
        assert data["precipitation"][1] == pytest.approx(2.0)

    def test_ecmwf_snowfall_converted_from_meters(self):
        """ECMWF sf is in meters; should be ×1000 before de-accumulation."""
        points = [
            self._make_point(snow=0.0),
            self._make_point(snow=0.005),  # 0.005 m = 5 mm water equiv
        ]
        data, _ = build_hourly_data(points, "aifs")
        # ×1000 → [0, 5.0] mm, de-accumulated → [0, 5.0] mm,
        # then ×100 for m→cm (existing conversion) → [0, 500.0]
        assert data["snowfall"][0] == pytest.approx(0.0)
        assert data["snowfall"][1] == pytest.approx(500.0)

    def test_ncep_precipitation_not_converted(self):
        """NCEP APCP is already in mm; should NOT get ×1000."""
        points = [
            self._make_point(precip=0.0),
            self._make_point(precip=2.0),  # 2 mm
        ]
        data, _ = build_hourly_data(points, "gfs")
        assert data["precipitation"][0] == pytest.approx(0.0)
        assert data["precipitation"][1] == pytest.approx(2.0)

    def test_ncep_snowfall_not_converted(self):
        """NCEP ASNOW is already in meters; should NOT get ×1000."""
        points = [
            self._make_point(snow=0.0),
            self._make_point(snow=0.05),  # 0.05 m
        ]
        data, _ = build_hourly_data(points, "gfs")
        # De-accumulated: [0, 0.05] m, ×100 → [0, 5.0] cm
        assert data["snowfall"][0] == pytest.approx(0.0)
        assert data["snowfall"][1] == pytest.approx(5.0)

    def test_ecmwf_none_values_preserved(self):
        """None values should pass through ×1000 conversion unchanged."""
        points = [
            self._make_point(precip=None, snow=None),
        ]
        data, _ = build_hourly_data(points, "ecmwf_ens")
        assert data["precipitation"][0] is None
        assert data["snowfall"][0] is None

    def test_all_ecmwf_model_ids_trigger_conversion(self):
        """All three ECMWF model IDs should trigger the ×1000 conversion."""
        for model_id in ("ifs", "aifs", "ecmwf_ens"):
            points = [
                self._make_point(precip=0.0),
                self._make_point(precip=0.001),  # 0.001 m = 1 mm
            ]
            data, _ = build_hourly_data(points, model_id)
            assert data["precipitation"][1] == pytest.approx(1.0), (
                f"{model_id} should convert precip from meters to mm"
            )
