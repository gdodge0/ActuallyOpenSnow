"""Tests for internal helper functions."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.main import (
    resolve_elevation,
    db_forecast_to_response,
    db_blend_to_response,
    get_resort_forecast_from_db,
    get_blend_description,
    check_unique_coords_limit,
    unique_coords_tracker,
)
from app.resorts import get_resort_by_slug


class TestResolveElevation:
    def test_summit_default(self):
        resort = get_resort_by_slug("jackson-hole")
        elev_m, elev_type = resolve_elevation(resort, None)
        assert elev_type == "summit"
        assert elev_m == resort.summit_elevation_m

    def test_summit_explicit(self):
        resort = get_resort_by_slug("jackson-hole")
        elev_m, elev_type = resolve_elevation(resort, "summit")
        assert elev_type == "summit"

    def test_base(self):
        resort = get_resort_by_slug("jackson-hole")
        elev_m, elev_type = resolve_elevation(resort, "base")
        assert elev_type == "base"
        assert elev_m == resort.base_elevation_m

    def test_numeric(self):
        resort = get_resort_by_slug("jackson-hole")
        elev_m, elev_type = resolve_elevation(resort, "3000")
        assert elev_m == 3000.0
        assert elev_type == "summit"

    def test_invalid_text(self):
        resort = get_resort_by_slug("jackson-hole")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            resolve_elevation(resort, "invalid")
        assert exc_info.value.status_code == 400

    def test_out_of_range(self):
        resort = get_resort_by_slug("jackson-hole")
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            resolve_elevation(resort, "99999")
        assert exc_info.value.status_code == 400


class TestDbForecastToResponse:
    def test_converts_forecast(self, sample_forecast_data):
        resort = get_resort_by_slug("jackson-hole")
        row = MagicMock()
        row.model_id = "gfs"
        row.elevation_type = "summit"
        row.run_datetime = datetime(2024, 1, 1)
        row.times_utc = sample_forecast_data["times_utc"]
        row.hourly_data = sample_forecast_data["hourly_data"]
        row.hourly_units = sample_forecast_data["hourly_units"]
        row.enhanced_hourly_data = sample_forecast_data["enhanced_hourly_data"]
        row.enhanced_hourly_units = sample_forecast_data["enhanced_hourly_units"]
        row.ensemble_ranges = None

        resp = db_forecast_to_response(row, resort)
        assert resp.model_id == "gfs"
        assert resp.lat == resort.lat
        assert resp.elevation_m == resort.summit_elevation_m

    def test_base_elevation(self, sample_forecast_data):
        resort = get_resort_by_slug("jackson-hole")
        row = MagicMock()
        row.model_id = "gfs"
        row.elevation_type = "base"
        row.run_datetime = datetime(2024, 1, 1)
        row.times_utc = sample_forecast_data["times_utc"]
        row.hourly_data = sample_forecast_data["hourly_data"]
        row.hourly_units = sample_forecast_data["hourly_units"]
        row.enhanced_hourly_data = None
        row.enhanced_hourly_units = None
        row.ensemble_ranges = None

        resp = db_forecast_to_response(row, resort)
        assert resp.elevation_m == resort.base_elevation_m


class TestDbBlendToResponse:
    def test_converts_blend(self, sample_forecast_data):
        resort = get_resort_by_slug("jackson-hole")
        row = MagicMock()
        row.elevation_type = "summit"
        row.times_utc = sample_forecast_data["times_utc"]
        row.hourly_data = sample_forecast_data["hourly_data"]
        row.hourly_units = sample_forecast_data["hourly_units"]
        row.enhanced_hourly_data = sample_forecast_data["enhanced_hourly_data"]
        row.enhanced_hourly_units = sample_forecast_data["enhanced_hourly_units"]
        row.ensemble_ranges = None
        row.source_model_runs = {"gfs": "2024-01-01T00:00:00", "ifs": "2024-01-01T00:00:00"}

        resp = db_blend_to_response(row, resort)
        assert resp.model_id == "blend"
        assert resp.model_run_utc == "2024-01-01T00:00:00"

    def test_blend_empty_source_runs(self, sample_forecast_data):
        resort = get_resort_by_slug("jackson-hole")
        row = MagicMock()
        row.elevation_type = "summit"
        row.times_utc = sample_forecast_data["times_utc"]
        row.hourly_data = sample_forecast_data["hourly_data"]
        row.hourly_units = sample_forecast_data["hourly_units"]
        row.enhanced_hourly_data = None
        row.enhanced_hourly_units = None
        row.ensemble_ranges = None
        row.source_model_runs = {}

        resp = db_blend_to_response(row, resort)
        assert resp.model_run_utc is None


class TestGetBlendDescription:
    def test_returns_string(self):
        desc = get_blend_description()
        assert "blend" in desc.lower()
        assert "HRRR" in desc


class TestUniqueCoordLimit:
    def test_allows_first_request(self):
        unique_coords_tracker.clear()
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        # Should not raise
        check_unique_coords_limit(request, 43.5, -110.8)

    def test_same_coords_dont_count(self):
        unique_coords_tracker.clear()
        request = MagicMock()
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        # First and second call for same coords
        check_unique_coords_limit(request, 43.5, -110.8)
        check_unique_coords_limit(request, 43.5, -110.8)
        # Should still only count as 1
        assert len(unique_coords_tracker["127.0.0.1"]) == 1
