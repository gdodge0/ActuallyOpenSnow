"""Tests for blend configuration and debug endpoints."""

from unittest.mock import patch


class TestBlendConfig:
    def test_returns_config(self, app_client):
        resp = app_client.get("/api/blend/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert "weights" in data
        assert "description" in data
        assert data["config_method"] == "engine_precomputed"

    def test_weights_include_new_models(self, app_client):
        resp = app_client.get("/api/blend/config")
        data = resp.json()
        assert "hrrr" in data["weights"]
        assert "gfs" in data["weights"]
        assert "gefs" in data["weights"]


class TestDebugBlend:
    def test_debug_blocked_in_production(self, app_client, monkeypatch):
        monkeypatch.setattr("app.main.PRODUCTION_MODE", True)
        resp = app_client.get("/api/blend/debug?lat=43.5&lon=-110.8")
        assert resp.status_code == 404

    def test_debug_works_in_dev(self, app_client, monkeypatch):
        monkeypatch.setattr("app.main.PRODUCTION_MODE", False)
        from app.resorts import get_resort_by_slug
        resort = get_resort_by_slug("jackson-hole")
        resp = app_client.get(f"/api/blend/debug?lat={resort.lat}&lon={resort.lon}")
        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data or "error" in data

    def test_debug_no_matching_resort(self, app_client, monkeypatch):
        monkeypatch.setattr("app.main.PRODUCTION_MODE", False)
        resp = app_client.get("/api/blend/debug?lat=0.0&lon=0.0")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
