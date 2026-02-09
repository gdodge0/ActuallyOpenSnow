"""Tests for model comparison endpoints."""

from unittest.mock import patch


class TestResortCompare:
    def test_compare_two_models(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/compare?models=gfs,ifs")
        assert resp.status_code == 200
        data = resp.json()
        assert "gfs" in data["forecasts"]
        assert "ifs" in data["forecasts"]

    def test_compare_includes_blend(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/compare?models=blend,gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert "blend" in data["forecasts"]
        assert "gfs" in data["forecasts"]

    def test_compare_nonexistent_resort(self, app_client):
        resp = app_client.get("/api/resorts/nonexistent/compare?models=gfs")
        assert resp.status_code == 404

    def test_compare_no_models_param(self, app_client):
        """Default models should be used."""
        resp = app_client.get("/api/resorts/jackson-hole/compare")
        assert resp.status_code == 200

    def test_compare_partial_data(self, app_client):
        """If some models have data and some don't, return what we have."""
        resp = app_client.get("/api/resorts/jackson-hole/compare?models=gfs,nonexistent_model")
        assert resp.status_code == 200
        data = resp.json()
        assert "gfs" in data["forecasts"]

    def test_compare_no_data_at_all(self, empty_app_client):
        resp = empty_app_client.get("/api/resorts/jackson-hole/compare?models=gfs,ifs")
        assert resp.status_code == 404

    def test_compare_base_elevation(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/compare?models=gfs&elevation=base")
        assert resp.status_code == 200

    def test_compare_response_shape(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole/compare?models=gfs")
        data = resp.json()
        assert "lat" in data
        assert "lon" in data
        assert "elevation_m" in data
        assert "forecasts" in data


class TestCoordinateCompare:
    def test_compare_known_coords(self, app_client):
        from app.resorts import get_resort_by_slug
        resort = get_resort_by_slug("jackson-hole")
        resp = app_client.get(f"/api/compare?lat={resort.lat}&lon={resort.lon}&models=gfs,ifs")
        assert resp.status_code == 200
        data = resp.json()
        assert "gfs" in data["forecasts"]

    def test_compare_custom_coords_no_engine(self, app_client):
        with patch("app.main.proxy_to_engine_backend", return_value=None):
            resp = app_client.get("/api/compare?lat=0.0&lon=0.0&models=gfs")
            assert resp.status_code == 404
