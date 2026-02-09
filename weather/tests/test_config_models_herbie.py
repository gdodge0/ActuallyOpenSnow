"""Tests for Herbie-related model configuration extensions."""

import pytest
from weather.config.models import (
    ModelConfig,
    MODELS,
    MODEL_ALIASES,
    validate_model_id,
    get_model_config,
    get_fxx_range,
)
from weather.domain.errors import ModelError


class TestHerbieModelConfig:
    """Tests for Herbie fields on ModelConfig."""

    def test_herbie_fields_default_to_none(self):
        """Test that Herbie fields default to None/False."""
        config = ModelConfig(
            model_id="test",
            api_model="test_api",
            display_name="Test",
            provider="Provider",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description="Test model",
        )
        assert config.herbie_model is None
        assert config.herbie_product is None
        assert config.update_interval_hours == 6
        assert config.is_ensemble is False
        assert config.min_fxx == 0

    def test_herbie_fields_settable(self):
        """Test that Herbie fields can be set."""
        config = ModelConfig(
            model_id="test",
            api_model="",
            display_name="Test",
            provider="Provider",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description="Test",
            herbie_model="hrrr",
            herbie_product="sfc",
            update_interval_hours=1,
            is_ensemble=False,
        )
        assert config.herbie_model == "hrrr"
        assert config.herbie_product == "sfc"
        assert config.update_interval_hours == 1

    def test_ensemble_flag(self):
        """Test ensemble flag on model configs."""
        config = ModelConfig(
            model_id="test_ens",
            api_model="",
            display_name="Test ENS",
            provider="Provider",
            max_forecast_days=16,
            resolution_degrees=0.25,
            description="Test ensemble",
            is_ensemble=True,
        )
        assert config.is_ensemble is True


class TestNewModels:
    """Tests for the new Herbie-based models."""

    def test_hrrr_model_exists(self):
        """Test HRRR model is registered."""
        assert "hrrr" in MODELS
        config = MODELS["hrrr"]
        assert config.model_id == "hrrr"
        assert config.provider == "NOAA"
        assert config.herbie_model == "hrrr"
        assert config.herbie_product == "sfc"
        assert config.update_interval_hours == 1
        assert config.max_forecast_days == 2
        assert config.api_model == ""
        assert config.is_ensemble is False

    def test_nbm_model_exists(self):
        """Test NBM model is registered."""
        assert "nbm" in MODELS
        config = MODELS["nbm"]
        assert config.model_id == "nbm"
        assert config.provider == "NOAA"
        assert config.herbie_model == "nbm"
        assert config.herbie_product == "co"
        assert config.update_interval_hours == 3

    def test_gefs_model_exists(self):
        """Test GEFS model is registered."""
        assert "gefs" in MODELS
        config = MODELS["gefs"]
        assert config.model_id == "gefs"
        assert config.provider == "NOAA"
        assert config.herbie_model == "gefs"
        assert config.herbie_product == "atmos.5"
        assert config.is_ensemble is True
        assert config.update_interval_hours == 6

    def test_ecmwf_ens_model_exists(self):
        """Test ECMWF ENS model is registered."""
        assert "ecmwf_ens" in MODELS
        config = MODELS["ecmwf_ens"]
        assert config.model_id == "ecmwf_ens"
        assert config.provider == "ECMWF"
        assert config.herbie_model == "ifs"
        assert config.herbie_product == "enfo"
        assert config.is_ensemble is True
        assert config.update_interval_hours == 12


class TestExistingModelsHerbieFields:
    """Tests that existing models have correct Herbie fields."""

    def test_gfs_has_herbie(self):
        """Test GFS model has Herbie fields."""
        config = MODELS["gfs"]
        assert config.herbie_model == "gfs"
        assert config.herbie_product == "pgrb2.0p25"
        assert config.update_interval_hours == 6
        # Still has Open-Meteo API access
        assert config.api_model == "gfs_seamless"

    def test_ifs_has_herbie(self):
        """Test IFS model has Herbie fields."""
        config = MODELS["ifs"]
        assert config.herbie_model == "ifs"
        assert config.herbie_product == "oper"
        assert config.update_interval_hours == 12

    def test_aifs_has_herbie(self):
        """Test AIFS model has Herbie fields."""
        config = MODELS["aifs"]
        assert config.herbie_model == "aifs"
        assert config.herbie_product == "oper"
        assert config.update_interval_hours == 12

    def test_icon_no_herbie(self):
        """Test ICON model has no Herbie fields."""
        config = MODELS["icon"]
        assert config.herbie_model is None
        assert config.herbie_product is None

    def test_jma_no_herbie(self):
        """Test JMA model has no Herbie fields."""
        config = MODELS["jma"]
        assert config.herbie_model is None
        assert config.herbie_product is None


class TestNewAliases:
    """Tests for new model aliases."""

    def test_hrrr3km_alias(self):
        """Test hrrr3km alias."""
        assert validate_model_id("hrrr3km") == "hrrr"

    def test_ensemble_alias(self):
        """Test ensemble alias."""
        assert validate_model_id("ensemble") == "gefs"

    def test_ens_alias(self):
        """Test ens alias."""
        assert validate_model_id("ens") == "ecmwf_ens"

    def test_national_blend_alias(self):
        """Test national_blend alias."""
        assert validate_model_id("national_blend") == "nbm"

    def test_new_models_validate(self):
        """Test that new model IDs validate correctly."""
        assert validate_model_id("hrrr") == "hrrr"
        assert validate_model_id("nbm") == "nbm"
        assert validate_model_id("gefs") == "gefs"
        assert validate_model_id("ecmwf_ens") == "ecmwf_ens"

    def test_new_models_case_insensitive(self):
        """Test new model IDs are case-insensitive."""
        assert validate_model_id("HRRR") == "hrrr"
        assert validate_model_id("NBM") == "nbm"
        assert validate_model_id("GEFS") == "gefs"
        assert validate_model_id("ECMWF_ENS") == "ecmwf_ens"

    def test_get_config_for_new_models(self):
        """Test getting config for new models."""
        for model_id in ["hrrr", "nbm", "gefs", "ecmwf_ens"]:
            config = get_model_config(model_id)
            assert config.model_id == model_id
            assert config.herbie_model is not None


class TestGetFxxRange:
    """Tests for get_fxx_range() helper."""

    def test_hrrr_hourly_48(self):
        """HRRR: 0-48 hourly = 49 hours."""
        config = MODELS["hrrr"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 0
        assert fxx[-1] == 48
        assert len(fxx) == 49
        # All hourly
        assert all(fxx[i + 1] - fxx[i] == 1 for i in range(len(fxx) - 1))

    def test_gfs_hourly_then_3h(self):
        """GFS: 0-120 hourly + 123-384 every 3h = 209 hours."""
        config = MODELS["gfs"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 0
        assert fxx[-1] == 384
        assert len(fxx) == 209
        # First 121 are hourly (0-120)
        assert fxx[120] == 120
        # After 120, steps are 3h
        assert fxx[121] == 123
        assert fxx[122] == 126

    def test_nbm_hourly_then_3h(self):
        """NBM: 0-36 hourly + 39-168 every 3h = 81 hours."""
        config = MODELS["nbm"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 0
        assert fxx[-1] == 168
        assert len(fxx) == 81

    def test_ifs_3h_then_6h(self):
        """IFS: 3-144 every 3h + 150-240 every 6h = 64 hours (min_fxx=3)."""
        config = MODELS["ifs"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 3
        assert fxx[-1] == 240
        assert len(fxx) == 64

    def test_aifs_6h(self):
        """AIFS: 6-360 every 6h = 60 hours (min_fxx=6)."""
        config = MODELS["aifs"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 6
        assert fxx[-1] == 360
        assert len(fxx) == 60

    def test_gefs_3h_then_6h(self):
        """GEFS: 3-240 every 3h + 246-384 every 6h = 104 hours (min_fxx=3)."""
        config = MODELS["gefs"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 3
        assert fxx[-1] == 384
        assert len(fxx) == 104

    def test_ecmwf_ens_3h_then_6h(self):
        """ECMWF ENS: 3-144 every 3h + 150-360 every 6h = 84 hours (min_fxx=3)."""
        config = MODELS["ecmwf_ens"]
        fxx = get_fxx_range(config)
        assert fxx[0] == 3
        assert fxx[-1] == 360
        assert len(fxx) == 84

    def test_no_forecast_steps_uses_max_days(self):
        """Models without forecast_steps fall back to max_forecast_days * 24."""
        config = ModelConfig(
            model_id="test",
            api_model="test",
            display_name="Test",
            provider="Test",
            max_forecast_days=2,
            resolution_degrees=0.25,
            description="Test",
        )
        fxx = get_fxx_range(config)
        assert fxx[0] == 0
        assert fxx[-1] == 48
        assert len(fxx) == 49

    def test_no_duplicates(self):
        """Verify no duplicate hours in any model's fxx range."""
        for model_id, config in MODELS.items():
            if config.forecast_steps is not None:
                fxx = get_fxx_range(config)
                assert len(fxx) == len(set(fxx)), f"Duplicates in {model_id}"

    def test_sorted_ascending(self):
        """Verify all fxx ranges are sorted ascending."""
        for model_id, config in MODELS.items():
            if config.forecast_steps is not None:
                fxx = get_fxx_range(config)
                assert fxx == sorted(fxx), f"Not sorted for {model_id}"

    def test_min_fxx_default_is_zero(self):
        """Models without explicit min_fxx default to 0."""
        config = ModelConfig(
            model_id="test",
            api_model="test",
            display_name="Test",
            provider="Test",
            max_forecast_days=2,
            resolution_degrees=0.25,
            description="Test",
        )
        assert config.min_fxx == 0

    def test_min_fxx_filters_no_forecast_steps(self):
        """min_fxx shifts the start when forecast_steps is None."""
        config = ModelConfig(
            model_id="test",
            api_model="test",
            display_name="Test",
            provider="Test",
            max_forecast_days=1,
            resolution_degrees=0.25,
            description="Test",
            min_fxx=6,
        )
        fxx = get_fxx_range(config)
        assert fxx[0] == 6
        assert fxx[-1] == 24
        assert len(fxx) == 19

    def test_min_fxx_filters_with_forecast_steps(self):
        """min_fxx filters out hours below the threshold with forecast_steps."""
        config = ModelConfig(
            model_id="test",
            api_model="test",
            display_name="Test",
            provider="Test",
            max_forecast_days=2,
            resolution_degrees=0.25,
            description="Test",
            forecast_steps=((48, 3),),
            min_fxx=6,
        )
        fxx = get_fxx_range(config)
        assert fxx[0] == 6
        assert fxx[-1] == 48
        assert 0 not in fxx
        assert 3 not in fxx

    def test_ecmwf_models_have_nonzero_min_fxx(self):
        """ECMWF models (IFS, AIFS, ECMWF ENS) skip fxx=0."""
        assert MODELS["ifs"].min_fxx == 3
        assert MODELS["aifs"].min_fxx == 6
        assert MODELS["ecmwf_ens"].min_fxx == 3

    def test_noaa_models_include_fxx_zero(self):
        """NOAA models (GFS, HRRR, NBM) include fxx=0."""
        for model_id in ("gfs", "hrrr", "nbm"):
            config = MODELS[model_id]
            assert config.min_fxx == 0, f"{model_id} should have min_fxx=0"
            fxx = get_fxx_range(config)
            assert fxx[0] == 0, f"{model_id} fxx should start at 0"
