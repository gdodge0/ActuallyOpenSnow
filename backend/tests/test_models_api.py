"""Tests for model listing endpoints."""


class TestGetModels:
    def test_lists_models(self, app_client):
        resp = app_client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_blend_is_first(self, app_client):
        resp = app_client.get("/api/models")
        data = resp.json()
        assert data[0]["model_id"] == "blend"
        assert data[0]["provider"] == "ActuallyOpenSnow"

    def test_model_fields(self, app_client):
        resp = app_client.get("/api/models")
        data = resp.json()
        for model in data:
            assert "model_id" in model
            assert "display_name" in model
            assert "provider" in model
            assert "max_forecast_days" in model
            assert "resolution_degrees" in model
            assert "description" in model


class TestGetModel:
    def test_get_blend_model(self, app_client):
        resp = app_client.get("/api/models/blend")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "blend"

    def test_get_gfs_model(self, app_client):
        resp = app_client.get("/api/models/gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["model_id"] == "gfs"

    def test_get_nonexistent_model(self, app_client):
        resp = app_client.get("/api/models/nonexistent")
        assert resp.status_code == 404
