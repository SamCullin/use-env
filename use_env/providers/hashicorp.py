"""
HashiCorp Vault provider (optional extra).

This module provides a provider that resolves secret references from HashiCorp Vault.

Reference Format:
    ${vault:<mount_point>/<path>}
    ${vault:<mount_point>/<path>/<field>}
    ${vault:secret/<path>}  # kv v2 default mount

Example:
    DATABASE_PASSWORD=${vault:secret/my-app/database}
    API_KEY=${vault:secret/my-app/api-key}
    DB_HOST=${vault:secret/my-app/host}

Install with: pip install use-env[vault]
"""

from __future__ import annotations

import re
from typing import Any

from hvac.exceptions import InvalidPath

from . import Provider, ProviderError, ProviderInfo


class HashiCorpVaultProvider(Provider):
    """
    HashiCorp Vault provider.

    Resolves secrets from HashiCorp Vault using the hvac library.

    Configuration:
        url: Vault server URL (default: VAULT_ADDR env var)
        token: Vault token (default: VAULT_TOKEN env var)
        namespace: Vault namespace (for Enterprise Vault)
        mount_point: Default mount point (default: secret)

    Install with: pip install use-env[vault]
    """

    info = ProviderInfo(
        name="vault",
        description="HashiCorp Vault provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<mount_point>[^/]+)/(?P<path>.+)$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        self._cache: dict[str, str] = {}
        self._url: str | None = None
        self._token: str | None = None
        self._namespace: str | None = None
        self._default_mount: str = "secret"

    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret from HashiCorp Vault.

        Args:
            reference: Reference in format "mount_point/path" or "mount_point/path/field"

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
                f"Invalid HashiCorp Vault reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        mount_point = match.group("mount_point")
        path = match.group("path")

        # Fetch the secret
        try:
            value = await self._fetch_secret(mount_point, path)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret from HashiCorp Vault: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    async def _fetch_secret(self, mount_point: str, path: str) -> str:
        """Fetch a secret using hvac library."""
        try:
            import hvac
        except ImportError as exc:
            raise ProviderError(
                "hvac is required for vault provider. Install it with: pip install use-env[vault]",
                provider=self.info.name,
                reference=f"{mount_point}/{path}",
            ) from exc

        # Create client
        if self._client is None:
            url = self._url or "http://127.0.0.1:8200"
            token = self._token

            # Try environment variables if not provided
            if not token:
                import os

                token = os.environ.get("VAULT_TOKEN")

            if not token:
                raise ProviderError(
                    "Vault token not configured. Set VAULT_TOKEN env var or configure in .use-env.yaml",
                    provider=self.info.name,
                    reference=f"{mount_point}/{path}",
                )

            self._client = hvac.Client(url=url, token=token)

            if self._namespace:
                self._client.headers["X-Vault-Namespace"] = self._namespace

        # Parse path to separate path from field
        parts = path.split("/")
        secret_path = "/".join(parts[:-1]) if len(parts) > 1 else parts[0]
        field = parts[-1] if len(parts) > 1 else None

        # Read the secret
        try:
            # Try KV v2 first
            response = self._client.secrets.kv.v2.read_secret_version(
                path=secret_path, mount_point=mount_point
            )

            data = response.get("data", {}).get("data", {})

            if field:
                if field in data:
                    return str(data[field])
                else:
                    raise ProviderError(
                        f"Field '{field}' not found in secret at {mount_point}/{secret_path}",
                        provider=self.info.name,
                        reference=f"{mount_point}/{path}",
                    )

            # If no field specified and single key, return that
            if len(data) == 1:
                return list(data.values())[0]

            # Return the whole secret as JSON
            import json

            return json.dumps(data)

        except InvalidPath:
            # Try KV v1
            response = self._client.secrets.kv.v1.read_secret(
                path=secret_path, mount_point=mount_point
            )

            data = response.get("data", {})

            if field:
                if field in data:
                    return str(data[field])
                else:
                    raise ProviderError(
                        f"Field '{field}' not found in secret at {mount_point}/{secret_path}",
                        provider=self.info.name,
                        reference=f"{mount_point}/{path}",
                    )

            if len(data) == 1:
                return list(data.values())[0]

            import json

            return json.dumps(data)

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the HashiCorp Vault provider."""
        if "url" in config:
            self._url = config["url"]
        if "token" in config:
            self._token = config["token"]
        if "namespace" in config:
            self._namespace = config["namespace"]
        if "mount_point" in config:
            self._default_mount = config["mount_point"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._client = None


def create_provider() -> HashiCorpVaultProvider:
    """Factory function to create a HashiCorpVaultProvider instance."""
    return HashiCorpVaultProvider()


def register() -> None:
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(HashiCorpVaultProvider)
