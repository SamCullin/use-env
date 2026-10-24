"""
Azure Key Vault provider using Python SDK (optional extra).

This module provides a provider that resolves secret references from Azure Key Vault
using the Azure SDK instead of the CLI.

Reference Format:
    ${azure-keyvault://<vault_name>/<secret_name>}
    ${azure-keyvault:<vault_name>/<secret_name>}

Example:
    DATABASE_PASSWORD=${azure-keyvault:my-keyvault/db-password}
    API_KEY=${azure-keyvault:production-vault/api-key}

Install with: pip install use-env[azure]
"""

from __future__ import annotations

import re
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class AzureKeyVaultProvider(Provider):
    """
    Azure Key Vault provider using Python SDK.

    Resolves secrets from Azure Key Vault using azure-identity and azure-keyvault-secrets.

    Configuration:
        tenant_id: Azure tenant ID (optional, uses default credential)
        client_id: Azure client ID (optional, uses default credential)
        client_secret: Azure client secret (optional, uses default credential)

    Install with: pip install use-env[azure]
    """

    info = ProviderInfo(
        name="azure-keyvault",
        description="Azure Key Vault provider (SDK-based)",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<vault_name>[^/]+)/(?P<secret_name>.+)$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        self._cache: dict[str, str] = {}

    async def resolve(self, reference: str) -> str:
        """
        Resolve a Key Vault secret reference.

        Args:
            reference: Reference in format "vault_name/secret_name"

        Returns:
            The secret value from Key Vault

        Raises:
            ProviderError: If the secret cannot be resolved
        """
        # Check cache first
        if reference in self._cache:
            return self._cache[reference]

        # Parse the reference
        match = re.match(self.info.reference_pattern, reference)
        if not match:
            raise ProviderError(
                f"Invalid Azure Key Vault reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        vault_name = match.group("vault_name")
        secret_name = match.group("secret_name")

        # Fetch the secret
        try:
            value = await self._fetch_secret(vault_name, secret_name)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret from Azure Key Vault: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    async def _fetch_secret(self, vault_name: str, secret_name: str) -> str:
        """Fetch a secret using Azure SDK."""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
        except ImportError as exc:
            raise ProviderError(
                "Azure SDK is required for azure-keyvault provider. "
                "Install it with: pip install use-env[azure]",
                provider=self.info.name,
                reference=f"{vault_name}/{secret_name}",
            ) from exc

        # Create client
        vault_url = f"https://{vault_name}.vault.azure.net"

        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = SecretClient(vault_url=vault_url, credential=credential)

        # Get the secret
        secret = self._client.get_secret(secret_name)
        if secret.value is None:
            raise ProviderError(
                f"Secret '{secret_name}' has no value",
                provider=self.info.name,
                reference=f"{vault_name}/{secret_name}",
            )
        return secret.value

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the Azure Key Vault provider."""
        if "tenant_id" in config:
            self._tenant_id = config["tenant_id"]
        if "client_id" in config:
            self._client_id = config["client_id"]
        if "client_secret" in config:
            self._client_secret = config["client_secret"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._client = None


def create_provider() -> AzureKeyVaultProvider:
    """Factory function to create an AzureKeyVaultProvider instance."""
    return AzureKeyVaultProvider()


def register() -> None:
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(AzureKeyVaultProvider)
