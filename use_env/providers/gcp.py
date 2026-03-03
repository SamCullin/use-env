"""
Google Cloud Secret Manager provider (optional extra).

This module provides a provider that resolves secret references from GCP Secret Manager.

Reference Format:
    ${gcp-secrets:<project_id>/<secret_name>}
    ${gcp-secrets:<project_id>/<secret_name>/<version>}

Example:
    DATABASE_PASSWORD=${gcp-secrets:my-project/db-password}
    API_KEY=${gcp-secrets:my-project/api-key/latest}

Install with: pip install use-env[gcp]
"""

from __future__ import annotations

import re
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class GcpSecretsProvider(Provider):
    """
    Google Cloud Secret Manager provider.

    Resolves secrets from GCP Secret Manager using google-cloud-secret-manager.

    Configuration:
        project_id: GCP project ID (optional, uses default)

    Install with: pip install use-env[gcp]
    """

    info = ProviderInfo(
        name="gcp-secrets",
        description="Google Cloud Secret Manager provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<project_id>[^/]+)/(?P<secret_name>[^/]+)(?:/(?P<version>.+))?$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        self._cache: dict[str, str] = {}
        self._default_project: str | None = None

    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret from GCP Secret Manager.

        Args:
            reference: Reference in format "project_id/secret_name" or "project_id/secret_name/version"

        Returns:
            The secret value

        Raises:
            ProviderError: If resolution fails
        """
        # Check cache first
        if reference in self._cache:
            return self._cache[reference]

        # Parse the reference
        match = re.match(self.info.reference_pattern, reference)
        if not match:
            raise ProviderError(
                f"Invalid GCP Secret Manager reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        project_id = match.group("project_id")
        secret_name = match.group("secret_name")
        version = match.group("version") or "latest"

        # Fetch the secret
        try:
            value = await self._fetch_secret(project_id, secret_name, version)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret from GCP Secret Manager: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    async def _fetch_secret(self, project_id: str, secret_name: str, version: str) -> str:
        """Fetch a secret using GCP Secret Manager client."""
        try:
            from google.cloud import secretmanager
        except ImportError as exc:
            raise ProviderError(
                "google-cloud-secret-manager is required for gcp-secrets provider. "
                "Install it with: pip install use-env[gcp]",
                provider=self.info.name,
                reference=f"{project_id}/{secret_name}/{version}",
            ) from exc

        # Create client
        if self._client is None:
            self._client = secretmanager.SecretManagerServiceClient()

        # Build the secret path
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version}"

        # Access the secret
        response = self._client.access_secret_version(request={"name": name})

        # Return the payload
        return response.payload.data.decode("UTF-8")

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the GCP Secret Manager provider."""
        if "project_id" in config:
            self._default_project = config["project_id"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._client = None


def create_provider() -> GcpSecretsProvider:
    """Factory function to create a GcpSecretsProvider instance."""
    return GcpSecretsProvider()


def register() -> None:
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(GcpSecretsProvider)
