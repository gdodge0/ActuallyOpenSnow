"""Tests for health and utility endpoints."""


class TestHealthCheck:
    def test_health_returns_ok(self, app_client):
        resp = app_client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "actuallyopensnow-api"


class TestCacheStats:
    def test_cache_stats_returns(self, app_client):
        resp = app_client.get("/api/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "redis_cache" in data


class TestCacheClear:
    def test_clear_cache_dev_mode(self, app_client, monkeypatch):
        monkeypatch.setattr("app.main.PRODUCTION_MODE", False)
        resp = app_client.post("/api/cache/clear")
        assert resp.status_code == 200

    def test_clear_cache_blocked_in_production(self, app_client, monkeypatch):
        monkeypatch.setattr("app.main.PRODUCTION_MODE", True)
        resp = app_client.post("/api/cache/clear")
        assert resp.status_code == 404
