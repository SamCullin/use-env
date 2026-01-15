"""
Provider Interface and Registry for use-env.

This module defines the base provider interface that all secret providers must implement,
and provides a registry system for discovering and loading providers.

Usage:
    from use_env.providers import Provider, ProviderRegistry

    # Create a custom provider
    class MyProvider(Provider):
        name = "my_provider"
        description = "My custom secret provider"

        async def resolve(self, reference: str) -> str:
            # Implementation here
            pass

    # Register the provider
    ProviderRegistry.register(MyProvider)

    # Get a provider instance
    provider = ProviderRegistry.get("my_provider")
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProviderInfo:
    """Metadata about a provider."""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    reference_pattern: str = ""


@dataclass
class ResolutionResult:
    """Result of resolving a secret reference."""

    success: bool
    value: str = ""
    error: str = ""
    cache_hit: bool = False


class Provider(ABC):
    """
    Base class for all secret providers.

    Providers are responsible for resolving secret references from various sources
    such as vault services, environment variables, files, or APIs.

    To create a custom provider:
    1. Inherit from Provider
    2. Set the `info` class attribute with provider metadata
    3. Implement the `resolve` method
    4. Optionally implement `validate_reference` for reference validation
    5. Register the provider with ProviderRegistry.register()

    Example:
        class VaultProvider(Provider):
            info = ProviderInfo(
                name="vault",
                description="Azure Key Vault provider",
                reference_pattern=r"(?P<resource_group>[^/]+)/(?P<vault_name>[^/]+)/(?P<secret_name>.+)"
            )

            async def resolve(self, reference: str) -> str:
                # Parse reference and fetch secret
                pass
    """

    info: ProviderInfo

    @abstractmethod
    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret reference to its actual value.

        Args:
            reference: The reference string to resolve (e.g., "myvault/mysecret")

        Returns:
            The resolved secret value

        Raises:
            ProviderError: If resolution fails
        """
        ...

    def validate_reference(self, reference: str) -> bool:
        """
        Validate that a reference is well-formed for this provider.

        Args:
            reference: The reference string to validate

        Returns:
            True if the reference is valid, False otherwise

        The default implementation uses the info.reference_pattern if provided.
        Override this method for custom validation logic.
        """
        if not self.info.reference_pattern:
            return True

        return bool(re.match(self.info.reference_pattern, reference))

    async def resolve_batch(
        self, references: list[str], progress_callback: Any | None = None
    ) -> dict[str, str]:
        """
        Resolve multiple references efficiently.

        Override this method to implement batch resolution for providers
        that support it (e.g., API-based providers).

        Args:
            references: List of references to resolve
            progress_callback: Optional callback(reference, index, total) for progress

        Returns:
            Dictionary mapping references to resolved values
        """
        results: dict[str, str] = {}

        for i, ref in enumerate(references):
            if progress_callback:
                progress_callback(ref, i, len(references))

            results[ref] = await self.resolve(ref)

        return results

    async def close(self) -> None:
        """
        Cleanup resources when the provider is no longer needed.

        Override this method to implement cleanup logic such as
        closing network connections or releasing resources.
        """
        pass

    async def __aenter__(self) -> "Provider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()


class ProviderRegistry:
    """
    Registry for discovering and managing secret providers.

    The registry maintains a mapping of provider names to provider classes,
    allowing dynamic loading and instantiation of providers.
    """

    _providers: dict[str, type[Provider]] = {}
    _instances: dict[str, Provider] = {}
    _config: dict[str, dict[str, Any]] = {}

    @classmethod
    def register(cls, provider_class: type[Provider], name: str | None = None) -> None:
        """
        Register a provider class with the registry.

        Args:
            provider_class: The provider class to register
            name: Optional custom name, defaults to provider.info.name

        Raises:
            ValueError: If provider class is missing required attributes
            KeyError: If a provider with the same name is already registered
        """
        if not hasattr(provider_class, "info") or not isinstance(provider_class.info, ProviderInfo):
            raise ValueError(
                f"Provider {provider_class.__name__} must have a ProviderInfo attribute"
            )

        provider_name = name or provider_class.info.name

        if provider_name in cls._providers:
            raise KeyError(f"Provider '{provider_name}' is already registered")

        cls._providers[provider_name] = provider_class

    @classmethod
    def get(cls, name: str, config: dict[str, Any] | None = None) -> Provider:
        """
        Get an instance of a provider by name.

        Args:
            name: The name of the provider to get
            config: Optional configuration for the provider instance

        Returns:
            An instance of the requested provider

        Raises:
            KeyError: If no provider with the given name is registered
        """
        if name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise KeyError(f"Provider '{name}' not found. Available providers: {available}")

        # Cache instances for reuse
        if name not in cls._instances or config is not None:
            provider_class = cls._providers[name]
            instance = provider_class()

            if config:
                cls._config[name] = config
                if hasattr(instance, "configure"):
                    instance.configure(config)

            cls._instances[name] = instance

        return cls._instances[name]

    @classmethod
    def list_providers(cls) -> list[ProviderInfo]:
        """
        List all registered providers with their metadata.

        Returns:
            List of ProviderInfo objects for all registered providers
        """
        return [provider.info for provider in cls._providers.values()]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """
        Check if a provider is registered.

        Args:
            name: The name of the provider to check

        Returns:
            True if the provider is registered, False otherwise
        """
        return name in cls._providers

    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers and instances."""
        for name, instance in cls._instances.items():
            if hasattr(instance, "close"):
                import asyncio

                try:
                    asyncio.run(instance.close())
                except Exception:
                    pass

        cls._providers.clear()
        cls._instances.clear()
        cls._config.clear()

    @classmethod
    def discover_plugins(cls, entry_point_group: str = "use_env.providers") -> None:
        """
        Discover and register providers from installed packages.

        This method looks for providers registered as entry points
        by installed packages.

        Args:
            entry_point_group: The entry point group name to search
        """
        try:
            from importlib.metadata import entry_points

            eps = entry_points(group=entry_point_group)

            for ep in eps:
                try:
                    provider_class = ep.load()
                    if isinstance(provider_class, type) and issubclass(provider_class, Provider):
                        cls.register(provider_class)
                except Exception:
                    pass
        except Exception:
            # Older Python versions or environments
            pass


class ProviderError(Exception):
    """Base exception for provider-related errors."""

    def __init__(self, message: str, provider: str | None = None, reference: str | None = None):
        self.message = message
        self.provider = provider
        self.reference = reference
        super().__init__(message)

    def __str__(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.insert(0, f"[{self.provider}]")
        if self.reference:
            parts.append(f"(reference: {self.reference})")
        return " ".join(parts)
