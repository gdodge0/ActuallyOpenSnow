"""Tests for model configuration and registry."""

import pytest
from weather.config.models import (
    ModelConfig,
    MODELS,
    MODEL_ALIASES,
    validate_model_id,
    get_model_config,
    list_available_models,
)
from weather.domain.errors import ModelError


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_model_config_creation(self):
        """Test creating a ModelConfig."""
        config = ModelConfig(
            model_id="test",
            api_model="test_model",
            display_name="Test Model",
            provider="Test Provider",
            max_forecast_days=10,
            resolution_degrees=0.25,
            description="A test model",
        )

        assert config.model_id == "test"
        assert config.api_model == "test_model"
        assert config.display_name == "Test Model"
        assert config.provider == "Test Provider"
        assert config.max_forecast_days == 10
        assert config.resolution_degrees == 0.25
        assert config.description == "A test model"

    def test_model_config_immutable(self):
        """Test that ModelConfig is immutable (frozen)."""
        config = MODELS["gfs"]

        with pytest.raises(AttributeError):
            config.model_id = "modified"

    def test_model_config_equality(self):
        """Test ModelConfig equality."""
        config1 = ModelConfig(
            model_id="test",
            api_model="test_api",
            display_name="Test",
            provider="Provider",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description="Desc",
        )
        config2 = ModelConfig(
            model_id="test",
            api_model="test_api",
            display_name="Test",
            provider="Provider",
            max_forecast_days=7,
            resolution_degrees=0.25,
            description="Desc",
        )

        assert config1 == config2


class TestModelsRegistry:
    """Tests for the MODELS registry."""

    def test_gfs_model_exists(self):
        """Test that GFS model is registered."""
        assert "gfs" in MODELS
        config = MODELS["gfs"]
        assert config.model_id == "gfs"
        assert config.provider == "NOAA"
        assert config.api_model == "gfs_seamless"

    def test_ifs_model_exists(self):
        """Test that IFS model is registered."""
        assert "ifs" in MODELS
        config = MODELS["ifs"]
        assert config.model_id == "ifs"
        assert config.provider == "ECMWF"

    def test_aifs_model_exists(self):
        """Test that AIFS model is registered."""
        assert "aifs" in MODELS
        config = MODELS["aifs"]
        assert config.model_id == "aifs"
        assert config.provider == "ECMWF"

    def test_icon_model_exists(self):
        """Test that ICON model is registered."""
        assert "icon" in MODELS
        config = MODELS["icon"]
        assert config.model_id == "icon"
        assert config.provider == "DWD"

    def test_jma_model_exists(self):
        """Test that JMA model is registered."""
        assert "jma" in MODELS
        config = MODELS["jma"]
        assert config.model_id == "jma"
        assert config.provider == "JMA"

    def test_all_models_have_required_fields(self):
        """Test that all models have required fields populated."""
        for model_id, config in MODELS.items():
            assert config.model_id == model_id
            assert config.api_model, f"{model_id} missing api_model"
            assert config.display_name, f"{model_id} missing display_name"
            assert config.provider, f"{model_id} missing provider"
            assert config.max_forecast_days > 0, f"{model_id} invalid max_forecast_days"
            assert config.resolution_degrees > 0, f"{model_id} invalid resolution"
            assert config.description, f"{model_id} missing description"


class TestModelAliases:
    """Tests for MODEL_ALIASES."""

    def test_noaa_alias_for_gfs(self):
        """Test that 'noaa' is an alias for 'gfs'."""
        assert MODEL_ALIASES["noaa"] == "gfs"

    def test_ecmwf_alias_for_ifs(self):
        """Test that 'ecmwf' is an alias for 'ifs'."""
        assert MODEL_ALIASES["ecmwf"] == "ifs"

    def test_ai_alias_for_aifs(self):
        """Test that 'ai' is an alias for 'aifs'."""
        assert MODEL_ALIASES["ai"] == "aifs"

    def test_all_aliases_point_to_valid_models(self):
        """Test that all aliases point to valid models."""
        for alias, model_id in MODEL_ALIASES.items():
            assert model_id in MODELS, f"Alias '{alias}' points to unknown model '{model_id}'"


class TestValidateModelId:
    """Tests for validate_model_id function."""

    def test_valid_model_id(self):
        """Test validation of valid model IDs."""
        assert validate_model_id("gfs") == "gfs"
        assert validate_model_id("ifs") == "ifs"
        assert validate_model_id("aifs") == "aifs"
        assert validate_model_id("icon") == "icon"
        assert validate_model_id("jma") == "jma"

    def test_case_insensitive(self):
        """Test that validation is case-insensitive."""
        assert validate_model_id("GFS") == "gfs"
        assert validate_model_id("IFS") == "ifs"
        assert validate_model_id("AIFS") == "aifs"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert validate_model_id("  gfs  ") == "gfs"
        assert validate_model_id("\tifs\n") == "ifs"

    def test_alias_returns_canonical(self):
        """Test that aliases return canonical model ID."""
        assert validate_model_id("noaa") == "gfs"
        assert validate_model_id("ecmwf") == "ifs"
        assert validate_model_id("european") == "ifs"
        assert validate_model_id("ai") == "aifs"
        assert validate_model_id("german") == "icon"
        assert validate_model_id("dwd") == "icon"

    def test_alias_case_insensitive(self):
        """Test that aliases are case-insensitive."""
        assert validate_model_id("NOAA") == "gfs"
        assert validate_model_id("ECMWF") == "ifs"

    def test_invalid_model_raises_modelerror(self):
        """Test that invalid model ID raises ModelError."""
        with pytest.raises(ModelError) as exc_info:
            validate_model_id("invalid_model")

        assert "Unknown model" in str(exc_info.value)
        assert exc_info.value.model_id == "invalid_model"

    def test_error_message_lists_available_models(self):
        """Test that error message lists available models."""
        with pytest.raises(ModelError) as exc_info:
            validate_model_id("fake_model")

        error_msg = str(exc_info.value)
        assert "gfs" in error_msg
        assert "ifs" in error_msg


class TestGetModelConfig:
    """Tests for get_model_config function."""

    def test_returns_config_for_valid_id(self):
        """Test that valid model ID returns config."""
        config = get_model_config("gfs")
        assert isinstance(config, ModelConfig)
        assert config.model_id == "gfs"

    def test_returns_config_for_alias(self):
        """Test that alias returns correct config."""
        config = get_model_config("noaa")
        assert config.model_id == "gfs"

    def test_case_insensitive(self):
        """Test that lookup is case-insensitive."""
        config = get_model_config("GFS")
        assert config.model_id == "gfs"

    def test_invalid_id_raises_modelerror(self):
        """Test that invalid ID raises ModelError."""
        with pytest.raises(ModelError):
            get_model_config("nonexistent")

    def test_returns_correct_config_fields(self):
        """Test that returned config has correct fields."""
        config = get_model_config("ifs")

        assert config.model_id == "ifs"
        assert config.api_model == "ecmwf_ifs025"
        assert config.provider == "ECMWF"


class TestListAvailableModels:
    """Tests for list_available_models function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        models = list_available_models()
        assert isinstance(models, list)

    def test_returns_model_configs(self):
        """Test that list contains ModelConfig objects."""
        models = list_available_models()
        for model in models:
            assert isinstance(model, ModelConfig)

    def test_returns_all_models(self):
        """Test that all registered models are returned."""
        models = list_available_models()
        model_ids = {m.model_id for m in models}

        assert model_ids == set(MODELS.keys())

    def test_length_matches_registry(self):
        """Test that list length matches registry."""
        models = list_available_models()
        assert len(models) == len(MODELS)

