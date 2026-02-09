"""Tests for blend computation logic."""

import pytest

from engine.services.blend_service import compute_blend, compute_ensemble_ranges


class TestComputeBlend:
    """Tests for weighted-average blend computation."""

    def _make_forecast(self, temp=None, snow=None, precip=None, enhanced_snow=None, rain=None):
        """Helper to create minimal forecast data dicts."""
        hourly_data = {}
        if temp is not None:
            hourly_data["temperature_2m"] = temp
        if snow is not None:
            hourly_data["snowfall"] = snow
        if precip is not None:
            hourly_data["precipitation"] = precip

        result = {
            "times_utc": [f"2024-01-01T{i:02d}:00:00" for i in range(len(temp or snow or precip or []))],
            "hourly_data": hourly_data,
            "hourly_units": {"temperature_2m": "C", "snowfall": "cm", "precipitation": "mm"},
        }

        if enhanced_snow is not None or rain is not None:
            result["enhanced_hourly_data"] = {}
            if enhanced_snow is not None:
                result["enhanced_hourly_data"]["enhanced_snowfall"] = enhanced_snow
            if rain is not None:
                result["enhanced_hourly_data"]["rain"] = rain

        return result

    def test_empty_forecasts_raises(self):
        with pytest.raises(ValueError, match="No forecasts"):
            compute_blend({})

    def test_single_model_passthrough(self):
        forecast = self._make_forecast(temp=[-5.0, -6.0])
        result = compute_blend({"gfs": forecast}, {"gfs": 1.0})

        assert result["hourly_data"]["temperature_2m"] == [-5.0, -6.0]

    def test_equal_weights_average(self):
        f1 = self._make_forecast(temp=[-4.0, -8.0])
        f2 = self._make_forecast(temp=[-6.0, -12.0])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        assert result["hourly_data"]["temperature_2m"][0] == pytest.approx(-5.0)
        assert result["hourly_data"]["temperature_2m"][1] == pytest.approx(-10.0)

    def test_weighted_average(self):
        """GFS at 3x, IFS at 1x: result should be closer to GFS."""
        f1 = self._make_forecast(temp=[-4.0])
        f2 = self._make_forecast(temp=[-8.0])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 3.0, "ifs": 1.0},
        )

        # (-4*3 + -8*1) / 4 = -20/4 = -5.0
        assert result["hourly_data"]["temperature_2m"][0] == pytest.approx(-5.0)

    def test_missing_variable_in_one_model(self):
        f1 = self._make_forecast(temp=[-5.0], snow=[1.0])
        f2 = self._make_forecast(temp=[-7.0])  # No snowfall

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        # Snowfall only from GFS
        assert result["hourly_data"]["snowfall"][0] == pytest.approx(1.0)
        # Temperature averaged
        assert result["hourly_data"]["temperature_2m"][0] == pytest.approx(-6.0)

    def test_none_values_excluded(self):
        f1 = self._make_forecast(temp=[None])
        f2 = self._make_forecast(temp=[-8.0])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        assert result["hourly_data"]["temperature_2m"][0] == pytest.approx(-8.0)

    def test_all_none_returns_none(self):
        f1 = self._make_forecast(temp=[None])
        f2 = self._make_forecast(temp=[None])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        assert result["hourly_data"]["temperature_2m"][0] is None

    def test_different_length_forecasts(self):
        """Uses minimum length."""
        f1 = self._make_forecast(temp=[-5.0, -6.0, -7.0])
        f2 = self._make_forecast(temp=[-5.0, -6.0])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        assert len(result["hourly_data"]["temperature_2m"]) == 2
        assert len(result["times_utc"]) == 2

    def test_enhanced_data_blended(self):
        f1 = self._make_forecast(temp=[-5.0], enhanced_snow=[1.0], rain=[0.0])
        f2 = self._make_forecast(temp=[-5.0], enhanced_snow=[3.0], rain=[0.5])

        result = compute_blend(
            {"gfs": f1, "ifs": f2},
            {"gfs": 1.0, "ifs": 1.0},
        )

        assert result["enhanced_hourly_data"]["enhanced_snowfall"][0] == pytest.approx(2.0)
        assert result["enhanced_hourly_data"]["rain"][0] == pytest.approx(0.25)

    def test_blend_with_multiple_models(self):
        """Test with HRRR(3), GFS(2), NBM(2), IFS(2) weights."""
        f_hrrr = self._make_forecast(temp=[-10.0])
        f_gfs = self._make_forecast(temp=[-5.0])
        f_nbm = self._make_forecast(temp=[-6.0])
        f_ifs = self._make_forecast(temp=[-4.0])

        result = compute_blend(
            {"hrrr": f_hrrr, "gfs": f_gfs, "nbm": f_nbm, "ifs": f_ifs},
            {"hrrr": 3.0, "gfs": 2.0, "nbm": 2.0, "ifs": 2.0},
        )

        # (-10*3 + -5*2 + -6*2 + -4*2) / 9 = (-30 - 10 - 12 - 8) / 9 = -60/9 ≈ -6.67
        expected = (-10 * 3 + -5 * 2 + -6 * 2 + -4 * 2) / 9
        assert result["hourly_data"]["temperature_2m"][0] == pytest.approx(expected)


class TestComputeEnsembleRanges:
    """Tests for ensemble range computation."""

    def test_empty_forecasts(self):
        result = compute_ensemble_ranges({})
        assert result == {}

    def test_single_ensemble(self):
        forecast = {
            "times_utc": ["2024-01-01T00:00:00"],
            "hourly_data": {"temperature_2m": [-5.0]},
            "enhanced_hourly_data": {"enhanced_snowfall": [1.5]},
        }
        result = compute_ensemble_ranges({"gefs": forecast})

        assert "enhanced_snowfall" in result
        assert "temperature_2m" in result

    def test_percentile_ordering(self):
        """P10 should be <= P90."""
        f1 = {
            "times_utc": ["2024-01-01T00:00:00"],
            "hourly_data": {"temperature_2m": [-5.0]},
            "enhanced_hourly_data": {"enhanced_snowfall": [1.0]},
        }
        f2 = {
            "times_utc": ["2024-01-01T00:00:00"],
            "hourly_data": {"temperature_2m": [-10.0]},
            "enhanced_hourly_data": {"enhanced_snowfall": [5.0]},
        }

        result = compute_ensemble_ranges({"gefs": f1, "ecmwf_ens": f2})

        for var in result:
            for i in range(len(result[var]["p10"])):
                assert result[var]["p10"][i] <= result[var]["p90"][i]

    def test_custom_variables(self):
        forecast = {
            "times_utc": ["2024-01-01T00:00:00"],
            "hourly_data": {"wind_speed_10m": [25.0]},
            "enhanced_hourly_data": {},
        }
        result = compute_ensemble_ranges(
            {"gefs": forecast},
            variables=["wind_speed_10m"],
        )

        assert "wind_speed_10m" in result
        assert "temperature_2m" not in result
