"""Tests for geographic utility functions."""

import pytest
import math
from weather.utils.geo import (
    haversine_distance,
    coords_are_equivalent,
    round_coords,
    normalize_longitude,
)


class TestHaversineDistance:
    """Tests for haversine_distance function."""

    def test_same_point_returns_zero(self):
        """Test that distance between same point is zero."""
        distance = haversine_distance(43.5, -110.75, 43.5, -110.75)
        assert distance == 0.0

    def test_known_distance_new_york_to_la(self):
        """Test against known distance (NYC to LA ~3940 km)."""
        # New York City
        nyc_lat, nyc_lon = 40.7128, -74.0060
        # Los Angeles
        la_lat, la_lon = 34.0522, -118.2437

        distance = haversine_distance(nyc_lat, nyc_lon, la_lat, la_lon)
        # Expected ~3940 km, allow 1% error
        expected_km = 3940
        actual_km = distance / 1000
        assert abs(actual_km - expected_km) < expected_km * 0.01

    def test_known_distance_london_to_paris(self):
        """Test against known distance (London to Paris ~344 km)."""
        # London
        london_lat, london_lon = 51.5074, -0.1278
        # Paris
        paris_lat, paris_lon = 48.8566, 2.3522

        distance = haversine_distance(london_lat, london_lon, paris_lat, paris_lon)
        expected_km = 344
        actual_km = distance / 1000
        assert abs(actual_km - expected_km) < expected_km * 0.02

    def test_symmetry(self):
        """Test that distance is symmetric (A to B == B to A)."""
        lat1, lon1 = 43.5, -110.75
        lat2, lon2 = 44.0, -111.0

        dist_ab = haversine_distance(lat1, lon1, lat2, lon2)
        dist_ba = haversine_distance(lat2, lon2, lat1, lon1)
        assert dist_ab == dist_ba

    def test_short_distance_meters(self):
        """Test short distances (should be in meters)."""
        # Two points about 111 meters apart (0.001 degrees latitude)
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.001, 0.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)
        # At equator, 0.001 degrees ≈ 111 meters
        assert 100 < distance < 120

    def test_across_prime_meridian(self):
        """Test distance calculation across prime meridian."""
        lat1, lon1 = 51.0, -1.0
        lat2, lon2 = 51.0, 1.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)
        # Should be a reasonable positive distance
        assert distance > 0
        # About 140 km for 2 degrees longitude at 51°N
        assert 130000 < distance < 150000

    def test_across_date_line(self):
        """Test distance calculation across international date line."""
        lat1, lon1 = 0.0, 179.0
        lat2, lon2 = 0.0, -179.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)
        # 2 degrees at equator ≈ 222 km
        assert 200000 < distance < 250000

    def test_poles(self):
        """Test distance from north pole to south pole."""
        distance = haversine_distance(90.0, 0.0, -90.0, 0.0)
        # Half Earth's circumference ≈ 20,000 km
        expected_km = 20000
        actual_km = distance / 1000
        assert abs(actual_km - expected_km) < expected_km * 0.01


class TestCoordsAreEquivalent:
    """Tests for coords_are_equivalent function."""

    def test_same_point_is_equivalent(self):
        """Test that same point is equivalent."""
        assert coords_are_equivalent(43.5, -110.75, 43.5, -110.75)

    def test_points_within_threshold(self):
        """Test points within threshold are equivalent."""
        # Two points about 50 meters apart
        lat1, lon1 = 43.5000, -110.75
        lat2, lon2 = 43.5003, -110.75  # ~33m north

        assert coords_are_equivalent(lat1, lon1, lat2, lon2, threshold_meters=100)

    def test_points_outside_threshold(self):
        """Test points outside threshold are not equivalent."""
        # Two points about 1km apart
        lat1, lon1 = 43.5, -110.75
        lat2, lon2 = 43.51, -110.75  # ~1.1km north

        assert not coords_are_equivalent(lat1, lon1, lat2, lon2, threshold_meters=100)

    def test_default_threshold_is_100m(self):
        """Test that default threshold is 100 meters."""
        # Points ~50m apart should be equivalent with default
        lat1, lon1 = 0.0, 0.0
        lat2, lon2 = 0.00045, 0.0  # ~50m at equator

        assert coords_are_equivalent(lat1, lon1, lat2, lon2)

        # Points ~150m apart should not be equivalent with default
        lat3, lon3 = 0.00135, 0.0  # ~150m at equator
        assert not coords_are_equivalent(lat1, lon1, lat3, lon3)

    def test_custom_threshold(self):
        """Test with custom threshold values."""
        lat1, lon1 = 43.5, -110.75
        lat2, lon2 = 43.505, -110.75  # ~550m north

        # Not equivalent at 100m
        assert not coords_are_equivalent(lat1, lon1, lat2, lon2, threshold_meters=100)

        # Equivalent at 1000m
        assert coords_are_equivalent(lat1, lon1, lat2, lon2, threshold_meters=1000)

    def test_exact_threshold_boundary(self):
        """Test behavior at exact threshold boundary."""
        # Use a known distance and exact threshold
        lat1, lon1 = 0.0, 0.0
        # 0.001 degrees at equator ≈ 111 meters
        lat2, lon2 = 0.001, 0.0

        distance = haversine_distance(lat1, lon1, lat2, lon2)

        # At exact distance, should be equivalent (<=)
        assert coords_are_equivalent(lat1, lon1, lat2, lon2, threshold_meters=distance)

        # Just under distance, should not be equivalent
        assert not coords_are_equivalent(
            lat1, lon1, lat2, lon2, threshold_meters=distance - 1
        )


class TestRoundCoords:
    """Tests for round_coords function."""

    def test_default_precision_4(self):
        """Test default precision is 4 decimal places."""
        lat, lon = round_coords(43.123456789, -110.987654321)
        assert lat == 43.1235
        assert lon == -110.9877

    def test_custom_precision(self):
        """Test custom precision values."""
        lat, lon = round_coords(43.123456, -110.987654, precision=2)
        assert lat == 43.12
        assert lon == -110.99

    def test_precision_0(self):
        """Test precision 0 rounds to integers."""
        lat, lon = round_coords(43.6, -110.4, precision=0)
        assert lat == 44.0
        assert lon == -110.0

    def test_precision_6(self):
        """Test high precision (6 decimal places)."""
        lat, lon = round_coords(43.12345678, -110.98765432, precision=6)
        assert lat == 43.123457
        assert lon == -110.987654

    def test_returns_tuple(self):
        """Test that function returns a tuple."""
        result = round_coords(43.5, -110.75)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_negative_coordinates(self):
        """Test rounding of negative coordinates."""
        lat, lon = round_coords(-43.12345, -110.98765, precision=3)
        assert lat == -43.123
        assert lon == -110.988


class TestNormalizeLongitude:
    """Tests for normalize_longitude function."""

    def test_already_normalized(self):
        """Test that already normalized values are unchanged."""
        assert normalize_longitude(0.0) == 0.0
        assert normalize_longitude(180.0) == 180.0
        assert normalize_longitude(-180.0) == -180.0
        assert normalize_longitude(90.0) == 90.0
        assert normalize_longitude(-90.0) == -90.0

    def test_greater_than_180(self):
        """Test normalization of values > 180."""
        assert normalize_longitude(181.0) == -179.0
        assert normalize_longitude(270.0) == -90.0
        assert normalize_longitude(360.0) == 0.0
        assert normalize_longitude(450.0) == 90.0

    def test_less_than_minus_180(self):
        """Test normalization of values < -180."""
        assert normalize_longitude(-181.0) == 179.0
        assert normalize_longitude(-270.0) == 90.0
        assert normalize_longitude(-360.0) == 0.0
        assert normalize_longitude(-450.0) == -90.0

    def test_multiple_rotations(self):
        """Test normalization with multiple full rotations."""
        # 720 degrees = 2 full rotations = 0
        assert normalize_longitude(720.0) == 0.0
        # -720 degrees = 2 full rotations = 0
        assert normalize_longitude(-720.0) == 0.0

    def test_boundary_values(self):
        """Test exact boundary values."""
        # Exactly 180 should stay 180
        assert normalize_longitude(180.0) == 180.0
        # Exactly -180 should stay -180
        assert normalize_longitude(-180.0) == -180.0

    def test_small_overflow(self):
        """Test small overflow past 180."""
        result = normalize_longitude(180.5)
        assert result == -179.5

    def test_small_underflow(self):
        """Test small underflow past -180."""
        result = normalize_longitude(-180.5)
        assert result == 179.5

