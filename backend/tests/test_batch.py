"""Tests for batch forecast endpoint."""


class TestBatchForecasts:
    def test_single_resort(self, app_client):
        resp = app_client.get("/api/resorts/batch/forecast?slugs=jackson-hole")
        assert resp.status_code == 200
        data = resp.json()
        assert "jackson-hole" in data["forecasts"]
        assert len(data["errors"]) == 0

    def test_multiple_resorts_partial(self, app_client):
        resp = app_client.get("/api/resorts/batch/forecast?slugs=jackson-hole,nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert "jackson-hole" in data["forecasts"]
        assert "nonexistent" in data["errors"]

    def test_empty_slugs(self, app_client):
        resp = app_client.get("/api/resorts/batch/forecast?slugs=")
        assert resp.status_code == 400

    def test_too_many_slugs(self, app_client):
        slugs = ",".join([f"resort-{i}" for i in range(21)])
        resp = app_client.get(f"/api/resorts/batch/forecast?slugs={slugs}")
        assert resp.status_code == 400

    def test_batch_with_model(self, app_client):
        resp = app_client.get("/api/resorts/batch/forecast?slugs=jackson-hole&model=gfs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["forecasts"]["jackson-hole"]["model_id"] == "gfs"

    def test_batch_base_elevation(self, app_client):
        resp = app_client.get("/api/resorts/batch/forecast?slugs=jackson-hole&model=gfs&elevation=base")
        assert resp.status_code == 200


class TestBatchNoData:
    def test_batch_no_forecast_data(self, empty_app_client):
        resp = empty_app_client.get("/api/resorts/batch/forecast?slugs=jackson-hole")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["forecasts"]) == 0
        assert "jackson-hole" in data["errors"]
