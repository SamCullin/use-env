"""
Environment variable provider for use-env.

This module provides a provider that resolves references to existing environment variables.

Reference Format:
    ${env:<VARIABLE_NAME>}
    ${env://<VARIABLE_NAME>}  # Alternative format

Example:
    DATABASE_HOST=${env:DATABASE_HOST}
    API_URL=${env://API_URL}
    DEBUG_MODE=${env:DEBUG}
"""

from __future__ import annotations

import os
import re
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class EnvironmentProvider(Provider):
    """
    Environment variable provider.

    Resolves references to existing environment variables.
    Useful for passing through values from the current environment.

    Example:
        # In your .env.dev file:
        DATABASE_HOST=${env:DATABASE_HOST}
        APP_ENV=${env:APP_ENV}

        # These will use the current environment values
    """

    info = ProviderInfo(
        name="env",
        description="Environment variable provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<variable_name>[A-Za-z_][A-Za-z0-9_]*)$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._cache: dict[str, str] = {}

    async def resolve(self, reference: str) -> str:
        """
        Resolve an environment variable reference.

        Args:
            reference: The environment variable name

        Returns:
            The value of the environment variable

        Raises:
            ProviderError: If the variable is not set
        """
        # Check cache first
        if reference in self._cache:
            return self._cache[reference]

        # Parse the reference (remove env: prefix if present)
        match = re.match(self.info.reference_pattern, reference)
        if not match:
            # Try alternate format with env: prefix
            alt_pattern = r"^env:(?P<variable_name>[A-Za-z_][A-Za-z0-9_]*)$"
            match = re.match(alt_pattern, reference)
            if not match:
                raise ProviderError(
                    f"Invalid environment variable reference: {reference}",
                    provider=self.info.name,
                    reference=reference,
                )

        var_name = match.group("variable_name")

        # Get the value
        value = os.environ.get(var_name)

        if value is None:
            raise ProviderError(
                f"Environment variable '{var_name}' is not set",
                provider=self.info.name,
                reference=reference,
            )

        # Cache the result
        self._cache[reference] = value

        return value

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the environment provider with options."""
        if "cache_enabled" in config:
            self._cache_enabled = config["cache_enabled"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()


class FallbackProvider(Provider):
    """
    Fallback provider that tries multiple providers in sequence.

    Useful when you want to try environment variables first,
    then fall back to other providers.
    """

    info = ProviderInfo(
        name="fallback",
        description="Fallback provider that tries multiple sources",
        version="1.0.0",
        author="use-env contributors",
    )

    def __init__(self, providers: list[Provider] | None = None) -> None:
        super().__init__()
        self._providers = providers or []

    def add_provider(self, provider: Provider) -> None:
        """Add a provider to the fallback chain."""
        self._providers.append(provider)

    async def resolve(self, reference: str) -> str:
        """
        Try each provider in sequence until one succeeds.

        Args:
            reference: The reference to resolve

        Returns:
            The resolved value from the first successful provider

        Raises:
            ProviderError: If all providers fail
        """
        errors: list[str] = []

        for provider in self._providers:
            try:
                return await provider.resolve(reference)
            except ProviderError as e:
                errors.append(f"{provider.info.name}: {e.message}")

        raise ProviderError(
            f"All providers failed for '{reference}': {'; '.join(errors)}",
            provider=self.info.name,
            reference=reference,
        )


def create_provider() -> EnvironmentProvider:
    """Factory function to create an EnvironmentProvider instance."""
    return EnvironmentProvider()
