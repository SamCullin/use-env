"""
1Password Connect provider (optional extra).

This module provides a provider that resolves secret references from 1Password via Connect.

Reference Format:
    ${1password:<vault_uuid>/<item_uuid>/<section>/<field>}
    ${1password:<vault_uuid>/<item_uuid>/<field>}
    ${op://vaults/<vault_uuid>/items/<item_uuid>/<field>}

Example:
    DATABASE_PASSWORD=${1password:vault-id/item-id/section/password}
    API_KEY=${1password:vault-id/item-id/api-key}

Install with: pip install use-env[1password]

Note: Requires a running 1Password Connect server.
"""

from __future__ import annotations

import re
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class OnePasswordProvider(Provider):
    """
    1Password Connect provider.

    Resolves secrets from 1Password using the Connect REST API.

    Configuration:
        connect_url: 1Password Connect server URL
        connect_token: 1Password Connect server token

    Install with: pip install use-env[1password]

    Note: Requires a running 1Password Connect server.
    """

    info = ProviderInfo(
        name="1password",
        description="1Password Connect provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<vault_id>[^/]+)/(?P<item_id>[^/]+)(?:/(?P<section>[^/]+))?/(?P<field>.+)$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._session: Any | None = None
        self._cache: dict[str, str] = {}
        self._connect_url: str | None = None
        self._connect_token: str | None = None

    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret from 1Password.

        Args:
            reference: Reference in format "vault_id/item_id/section/field" or "vault_id/item_id/field"

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
                f"Invalid 1Password reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        vault_id = match.group("vault_id")
        item_id = match.group("item_id")
        section = match.group("section")
        field = match.group("field")

        # Fetch the secret
        try:
            value = await self._fetch_secret(vault_id, item_id, section, field)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret from 1Password: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    async def _fetch_secret(
        self, vault_id: str, item_id: str, section: str | None, field: str
    ) -> str:
        """Fetch a secret using 1Password Connect API."""
        try:
            import aiohttp
        except ImportError as exc:
            raise ProviderError(
                "aiohttp is required for 1password provider. "
                "Install it with: pip install use-env[1password]",
                provider=self.info.name,
                reference=f"{vault_id}/{item_id}/{section or ''}/{field}",
            ) from exc

        # Get configuration
        connect_url = self._connect_url
        connect_token = self._connect_token

        # Try environment variables
        if not connect_url:
            import os

            connect_url = os.environ.get("OP_CONNECT_HOST")
        if not connect_token:
            import os

            connect_token = os.environ.get("OP_CONNECT_TOKEN")

        if not connect_url or not connect_token:
            raise ProviderError(
                "1Password Connect not configured. Set OP_CONNECT_HOST and OP_CONNECT_TOKEN "
                "env vars or configure in .use-env.yaml",
                provider=self.info.name,
                reference=f"{vault_id}/{item_id}/{section or ''}/{field}",
            )

        # Build the API URL
        if not connect_url.endswith("/"):
            connect_url += "/"

        url = f"{connect_url}v1/vaults/{vault_id}/items/{item_id}/fields/{field}"

        # Make the request
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"Authorization": f"Bearer {connect_token}"},
            ) as response:
                if response.status == 401:
                    raise ProviderError(
                        "1Password Connect authentication failed - check your token",
                        provider=self.info.name,
                        reference=f"{vault_id}/{item_id}/{section or ''}/{field}",
                    )
                elif response.status == 404:
                    raise ProviderError(
                        f"1Password item or field not found: {vault_id}/{item_id}/{field}",
                        provider=self.info.name,
                        reference=f"{vault_id}/{item_id}/{section or ''}/{field}",
                    )
                elif not response.ok:
                    raise ProviderError(
                        f"1Password API error: {response.status} {response.reason}",
                        provider=self.info.name,
                        reference=f"{vault_id}/{item_id}/{section or ''}/{field}",
                    )

                data = await response.json()

                # Return the field value
                return data.get("value", "")

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the 1Password Connect provider."""
        if "connect_url" in config:
            self._connect_url = config["connect_url"]
        if "connect_token" in config:
            self._connect_token = config["connect_token"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        if self._session:
            await self._session.close()
        self._session = None


def create_provider() -> OnePasswordProvider:
    """Factory function to create a OnePasswordProvider instance."""
    return OnePasswordProvider()


def register() -> None:
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(OnePasswordProvider)
