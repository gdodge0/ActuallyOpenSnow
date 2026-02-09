"""Tests for resort listing endpoints."""


class TestGetResorts:
    def test_lists_resorts(self, app_client):
        resp = app_client.get("/api/resorts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0

    def test_resort_fields(self, app_client):
        resp = app_client.get("/api/resorts")
        data = resp.json()
        resort = data[0]
        assert "slug" in resort
        assert "name" in resort
        assert "state" in resort
        assert "country" in resort
        assert "lat" in resort
        assert "lon" in resort
        assert "base_elevation_m" in resort
        assert "summit_elevation_m" in resort

    def test_filter_by_state(self, app_client):
        resp = app_client.get("/api/resorts?state=CO")
        assert resp.status_code == 200
        data = resp.json()
        for r in data:
            assert r["state"].upper() == "CO"

    def test_filter_by_state_case_insensitive(self, app_client):
        resp_upper = app_client.get("/api/resorts?state=CO")
        resp_lower = app_client.get("/api/resorts?state=co")
        assert resp_upper.json() == resp_lower.json()


class TestGetResort:
    def test_get_known_resort(self, app_client):
        resp = app_client.get("/api/resorts/jackson-hole")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "jackson-hole"

    def test_get_nonexistent_resort(self, app_client):
        resp = app_client.get("/api/resorts/nonexistent-resort")
        assert resp.status_code == 404
