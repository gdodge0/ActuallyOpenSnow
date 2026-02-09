"""Tests for forecast endpoints (resort and coordinate-based)."""

from unittest.mock import patch


class TestResortForecast:
    def test_blend_forecast(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?model=blend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "blend"
        assert "hourly_data" in data
        assert "times_utc" in data
        assert "enhanced_hourly_data" in data

    def test_gfs_forecast(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?model=gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "gfs"

    def test_default_model_is_blend(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "blend"

    def test_summit_elevation(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?elevation=summit")
        assert resp.status_code == 200

    def test_base_elevation(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?elevation=base&model=gfs")
        assert resp.status_code == 200

    def test_nonexistent_resort(self, app_client):
        resp = app_client.get("/api/resorts/nonexistent/forecast")
        assert resp.status_code == 404

    def test_nonexistent_model_returns_404(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?model=nonexistent")
        assert resp.status_code == 404

    def test_invalid_elevation(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?elevation=invalid_text")
        assert resp.status_code == 400

    def test_elevation_out_of_range(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?elevation=99999")
        assert resp.status_code == 400

    def test_response_has_required_fields(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?model=gfs")
        data = resp.json()
        assert "lat" in data
        assert "lon" in data
        assert "api_lat" in data
        assert "api_lon" in data
        assert "elevation_m" in data
        assert "model_id" in data
        assert "model_run_utc" in data
        assert "times_utc" in data
        assert "hourly_data" in data
        assert "hourly_units" in data

    def test_blend_response_has_model_run_utc(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/forecast?model=blend")
        data = resp.json()
        assert data["model_run_utc"] is not None

    def test_no_data_returns_404(self, empty_app_client):
        resp = empty_app_client.get("/api/resorts/jackson-hole/forecast?model=gfs")
        assert resp.status_code == 404


class TestCoordinateForecast:
    def test_known_resort_coords(self, app_client):
        """Coords matching jackson-hole should return DB data."""
        from app.resorts import get_resort_by_slug
        resort = get_resort_by_slug("jackson-hole")
        resp = app_client.get(f"/api/forecast?lat={resort.lat}&lon={resort.lon}&model=blend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "blend"

    def test_custom_coords_no_engine_returns_404(self, app_client):
        """Custom coords with no engine-backend should 404."""
        with patch("app.main.proxy_to_engine_backend", return_value=None):
            resp = app_client.get("/api/forecast?lat=0.0&lon=0.0&model=blend")
            assert resp.status_code == 404

    def test_custom_coords_engine_proxy(self, app_client):
        """Custom coords should proxy to engine-backend."""
        from app.models import ForecastResponse

        mock_resp = ForecastResponse(
            lat=40.0, lon=-105.0, api_lat=40.0, api_lon=-105.0,
            elevation_m=3000.0, model_id="blend", model_run_utc=None,
            times_utc=["2024-01-01T00:00:00"],
            hourly_data={"temperature_2m": [-5.0]},
            hourly_units={"temperature_2m": "C"},
        )
        with patch("app.main.proxy_to_engine_backend", return_value=mock_resp):
            resp = app_client.get("/api/forecast?lat=40.0&lon=-105.0&model=blend")
            assert resp.status_code == 200

    def test_invalid_lat(self, app_client):
        resp = app_client.get("/api/forecast?lat=999&lon=0&model=blend")
        assert resp.status_code == 422

    def test_invalid_lon(self, app_client):
        resp = app_client.get("/api/forecast?lat=0&lon=999&model=blend")
        assert resp.status_code == 422
