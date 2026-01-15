"""
Configuration management for use-env.

This module handles loading and parsing configuration files for the tool,
including user-defined providers and global settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProviderConfig:
    """Configuration for a single provider."""

    name: str
    type: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class UseEnvConfig:
    """Main configuration for use-env."""

    providers: list[ProviderConfig] = field(default_factory=list)
    global_options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "UseEnvConfig":
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to the configuration file. If None, searches
                        for config in standard locations.

        Returns:
            A UseEnvConfig instance with the loaded configuration.
        """
        if config_path is None:
            config_path = cls._find_config_file()

        if config_path is None or not Path(config_path).exists():
            return cls()

        return cls._parse_config_file(config_path)

    @classmethod
    def _find_config_file(cls) -> str | None:
        """Search for config file in standard locations."""
        search_paths = [
            Path.cwd() / ".use-env.yaml",
            Path.cwd() / ".use-env.yml",
            Path.cwd() / "use-env.yaml",
            Path.cwd() / "use-env.yml",
            Path.home() / ".config" / "use-env.yaml",
            Path.home() / ".use-env.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return str(path)

        return None

    @classmethod
    def _parse_config_file(cls, config_path: str | Path) -> "UseEnvConfig":
        """Parse a YAML configuration file."""
        path = Path(config_path)

        try:
            data = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            raise ConfigurationError(f"Invalid YAML in config file: {exc}") from exc

        if data is None:
            return cls()

        providers = []
        for provider_data in data.get("providers", []):
            provider = ProviderConfig(
                name=provider_data.get("name", ""),
                type=provider_data.get("type", ""),
                enabled=provider_data.get("enabled", True),
                config=provider_data.get("config", {}),
            )
            providers.append(provider)

        return cls(
            providers=providers,
            global_options=data.get("options", {}),
        )

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        """Get configuration for a specific provider."""
        for provider in self.providers:
            if provider.name == provider_name:
                return provider
        return None


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""

    def __init__(self, message: str, from_exception: Exception | None = None) -> None:
        self.message = message
        self.from_exception = from_exception
        super().__init__(message)
        if from_exception:
            self.__cause__ = from_exception
