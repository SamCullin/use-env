"""Built-in provider loader for use-env.

This module registers all built-in providers with the ProviderRegistry.
"""

from . import ProviderRegistry
from .azure import AzureKeyVaultProvider
from .env import EnvironmentProvider
from .file import FileProvider

# Track whether providers have been registered
_registered = False


def register_built_in_providers() -> None:
    """Register all built-in providers with the registry.

    This function is idempotent - it can be called multiple times safely.
    """
    global _registered

    if _registered:
        return

    # Check if already registered before trying
    if not ProviderRegistry.is_registered("azure-keyvault"):
        ProviderRegistry.register(AzureKeyVaultProvider)
    if not ProviderRegistry.is_registered("env"):
        ProviderRegistry.register(EnvironmentProvider)
    if not ProviderRegistry.is_registered("file"):
        ProviderRegistry.register(FileProvider)

    _registered = True


# Auto-register on import
register_built_in_providers()
