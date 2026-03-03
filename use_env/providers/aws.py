"""
AWS Secrets Manager provider (optional extra).

This module provides a provider that resolves secret references from AWS Secrets Manager.

Reference Format:
    ${aws-secrets:<region>/<secret_name>}
    ${aws-secrets:<secret_name>}  # Uses default region

Example:
    DATABASE_PASSWORD=${aws-secrets:us-east-1/my-app/database}
    API_KEY=${aws-secrets:my-app/api-key}

Install with: pip install use-env[aws]
"""

from __future__ import annotations

import json
import re
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class AwsSecretsProvider(Provider):
    """
    AWS Secrets Manager provider.

    Resolves secrets from AWS Secrets Manager using boto3.

    Configuration:
        region: AWS region (default: uses default session)
        profile: AWS profile name (optional)

    Install with: pip install use-env[aws]
    """

    info = ProviderInfo(
        name="aws-secrets",
        description="AWS Secrets Manager provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<region>[^/]+)/(?P<secret_name>.+)$",
    )

    def __init__(self) -> None:
        super().__init__()
        self._session: Any | None = None
        self._cache: dict[str, str] = {}
        self._region: str | None = None
        self._profile: str | None = None

    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret from AWS Secrets Manager.

        Args:
            reference: Reference in format "region/secret_name" or just "secret_name"

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
            # Try simple format (just secret name, use default region)
            if "/" not in reference:
                raise ProviderError(
                    f"Invalid AWS Secrets reference format: {reference}. "
                    "Expected format: region/secret_name or use aws: prefix",
                    provider=self.info.name,
                    reference=reference,
                )
            raise ProviderError(
                f"Invalid AWS Secrets reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        region = match.group("region")
        secret_name = match.group("secret_name")

        # Fetch the secret
        try:
            value = await self._fetch_secret(region, secret_name)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret from AWS Secrets Manager: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    async def _fetch_secret(self, region: str, secret_name: str) -> str:
        """Fetch a secret using boto3."""
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise ProviderError(
                "boto3 is required for aws-secrets provider. "
                "Install it with: pip install use-env[aws]",
                provider=self.info.name,
                reference=f"{region}/{secret_name}",
            ) from exc

        # Create a session if not exists
        if self._session is None:
            if self._profile:
                import os

                os.environ["AWS_PROFILE"] = self._profile
            self._session = boto3.session.Session(region_name=region)

        client = self._session.client(service_name="secretsmanager", region_name=region)

        try:
            response = client.get_secret_value(SecretId=secret_name)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "DecryptionFailureException":
                raise ProviderError(
                    f"Secret '{secret_name}' cannot be decrypted - check KMS key",
                    provider=self.info.name,
                    reference=f"{region}/{secret_name}",
                ) from exc
            elif error_code == "ResourceNotFoundException":
                raise ProviderError(
                    f"Secret '{secret_name}' not found in region '{region}'",
                    provider=self.info.name,
                    reference=f"{region}/{secret_name}",
                ) from exc
            else:
                raise ProviderError(
                    f"AWS error: {exc}",
                    provider=self.info.name,
                    reference=f"{region}/{secret_name}",
                ) from exc

        # Return the secret value
        if "SecretString" in response:
            secret = json.loads(response["SecretString"])

            # If the secret is a JSON object with a single value, return just the value
            if isinstance(secret, dict):
                if len(secret) == 1:
                    return list(secret.values())[0]
                # If it has 'password' key, return that
                if "password" in secret:
                    return secret["password"]
                # If it has the same key as the secret name, return that
                if secret_name in secret:
                    return secret[secret_name]
                # Otherwise return the whole JSON
                return json.dumps(secret)

            return str(secret)
        else:
            # Binary secret
            return response["SecretBinary"].decode("utf-8")

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the AWS Secrets provider."""
        if "region" in config:
            self._region = config["region"]
        if "profile" in config:
            self._profile = config["profile"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._session = None


def create_provider() -> AwsSecretsProvider:
    """Factory function to create an AwsSecretsProvider instance."""
    return AwsSecretsProvider()


def register() -> None:
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(AwsSecretsProvider)
