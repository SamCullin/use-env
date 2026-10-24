"""
Tests for the configuration module.
"""

import tempfile
from pathlib import Path

import pytest

from use_env.config import ConfigurationError, ProviderConfig, UseEnvConfig


class TestProviderConfig:
    """Tests for the ProviderConfig dataclass."""

    def test_create_provider_config(self):
        """Test creating a ProviderConfig."""
        config = ProviderConfig(
            name="my_provider",
            type="custom",
            enabled=True,
            config={"option1": "value1"},
        )

        assert config.name == "my_provider"
        assert config.type == "custom"
        assert config.enabled is True
        assert config.config == {"option1": "value1"}

    def test_default_values(self):
        """Test default values."""
        config = ProviderConfig(name="test", type="test")

        assert config.enabled is True
        assert config.config == {}


class TestUseEnvConfig:
    """Tests for the UseEnvConfig class."""

    def test_empty_config(self):
        """Test creating an empty config."""
        config = UseEnvConfig()

        assert config.providers == []
        assert config.global_options == {}

    def test_load_nonexistent_file(self):
        """Test loading a nonexistent file returns empty config."""
        config = UseEnvConfig.load("/nonexistent/path/config.yaml")

        assert config.providers == []
        assert config.global_options == {}

    def test_load_valid_config(self, temp_dir):
        """Test loading a valid configuration file."""
        config_content = """
providers:
  - name: my_vault
    type: vault
    enabled: true
    config:
      subscription_id: "12345"

  - name: custom_provider
    type: custom
    enabled: false

options:
  strict: true
  verbose: 2
"""
        config_path = temp_dir / ".use-env.yaml"
        config_path.write_text(config_content)

        config = UseEnvConfig.load(str(config_path))

        assert len(config.providers) == 2

        vault_config = config.get_provider_config("my_vault")
        assert vault_config is not None
        assert vault_config.type == "vault"
        assert vault_config.enabled is True
        assert vault_config.config.get("subscription_id") == "12345"

        custom_config = config.get_provider_config("custom_provider")
        assert custom_config is not None
        assert custom_config.enabled is False

        assert config.global_options.get("strict") is True
        assert config.global_options.get("verbose") == 2

    def test_load_invalid_yaml(self, temp_dir):
        """Test that invalid YAML raises an error."""
        config_path = temp_dir / "invalid.yaml"
        config_path.write_text("invalid: yaml: content: [[[")

        with pytest.raises(ConfigurationError):
            UseEnvConfig.load(str(config_path))

    def test_load_empty_yaml(self, temp_dir):
        """Test loading an empty YAML file."""
        config_path = temp_dir / "empty.yaml"
        config_path.write_text("")

        config = UseEnvConfig.load(str(config_path))

        assert config.providers == []
        assert config.global_options == {}

    def test_get_provider_config(self, temp_dir):
        """Test getting a specific provider config."""
        config_content = """
providers:
  - name: provider1
    type: type1

  - name: provider2
    type: type2
"""
        config_path = temp_dir / "config.yaml"
        config_path.write_text(config_content)

        config = UseEnvConfig.load(str(config_path))

        result = config.get_provider_config("provider1")

        assert result is not None
        assert result.name == "provider1"

    def test_get_nonexistent_provider_config(self, temp_dir):
        """Test getting a nonexistent provider returns None."""
        config = UseEnvConfig()

        result = config.get_provider_config("nonexistent")

        assert result is None

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)


class TestConfigurationError:
    """Tests for the ConfigurationError exception."""

    def test_error_message(self):
        """Test error message."""
        error = ConfigurationError("Invalid YAML")

        assert str(error) == "Invalid YAML"

    def test_error_with_cause(self):
        """Test error with cause exception."""
        original = ValueError("Original error")
        error = ConfigurationError("Config error", from_exception=original)

        assert error.__cause__ == original
