"""
Example custom provider for use-env.

This example demonstrates how to create a custom provider for AWS Secrets Manager.
"""

from __future__ import annotations

import re
from typing import Any

from use_env.providers import Provider, ProviderError, ProviderInfo


class AwsSecretsProvider(Provider):
    """
    AWS Secrets Manager provider.

    Resolves secrets from AWS Secrets Manager.

    Reference Format:
        ${aws-secrets:<region>/<secret_name>}

    Example:
        DATABASE_PASSWORD=${aws-secrets:us-east-1/my-app/database}
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

    async def resolve(self, reference: str) -> str:
        """
        Resolve a secret from AWS Secrets Manager.

        Args:
            reference: Reference in format "region/secret_name"

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

            # Create a session if not exists
            if self._session is None:
                self._session = boto3.session.Session()

            client = self._session.client(service_name="secretsmanager", region_name=region)

            try:
                response = client.get_secret_value(SecretId=secret_name)
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "DecryptionFailureException":
                    raise ProviderError(
                        f"Secret '{secret_name}' cannot be decrypted",
                        provider=self.info.name,
                        reference=f"{region}/{secret_name}",
                    ) from exc
                elif exc.response["Error"]["Code"] == "ResourceNotFoundException":
                    raise ProviderError(
                        f"Secret '{secret_name}' not found in region '{region}'",
                        provider=self.info.name,
                        reference=f"{region}/{secret_name}",
                    ) from exc
                else:
                    raise

            # Return the secret value
            if "SecretString" in response:
                import json

                secret = json.loads(response["SecretString"])
                # If the secret is a JSON object, return the first value
                if isinstance(secret, dict) and len(secret) == 1:
                    return list(secret.values())[0]
                elif isinstance(secret, dict):
                    # Return the whole JSON if multiple values
                    return json.dumps(secret)
                return secret
            else:
                # Binary secret
                return response["SecretBinary"].decode("utf-8")

        except ImportError as exc:
            raise ProviderError(
                "boto3 is required for AWS Secrets Manager provider. "
                "Install it with: pip install boto3",
                provider=self.info.name,
                reference=f"{region}/{secret_name}",
            ) from exc

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the AWS Secrets provider."""
        if "profile" in config:
            import os

            os.environ["AWS_PROFILE"] = config["profile"]

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._session = None


def create_provider() -> AwsSecretsProvider:
    """Factory function to create an AwsSecretsProvider instance."""
    return AwsSecretsProvider()


# Registration code (run this to register the provider)
def register():
    """Register the provider with the global registry."""
    from use_env.providers import ProviderRegistry

    ProviderRegistry.register(AwsSecretsProvider)


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main():
        # Register the provider
        register()

        # Get the provider
        provider = ProviderRegistry.get("aws-secrets")

        # List providers
        for info in ProviderRegistry.list_providers():
            print(f"{info.name}: {info.description}")

        # Clean up
        await provider.close()

    asyncio.run(main())
