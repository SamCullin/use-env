# Provider Development Guide

This guide explains how to create custom providers for `use-env`.

## Overview

Providers are plugins that resolve secret references from various sources. Any external system that stores secrets can be exposed as a provider.

## Creating a Basic Provider

### Step 1: Create the Provider Class

```python
# my_provider.py
import re
from use_env.providers import Provider, ProviderInfo, ProviderRegistry, ProviderError

class MyCustomProvider(Provider):
    """
    My custom secret provider for Example Service.
    """
    info = ProviderInfo(
        name="my_custom",
        description="My custom provider for Example Service",
        version="1.0.0",
        author="Your Name",
        reference_pattern=r"^(?P<service>[^/]+)/(?P<secret>.+)$"
    )

    async def resolve(self, reference: str) -> str:
        """
        Resolve a reference using the Example Service API.

        Args:
            reference: Reference in format "service/secret-name"

        Returns:
            The secret value

        Raises:
            ProviderError: If resolution fails
        """
        # Parse the reference
        match = re.match(self.info.reference_pattern, reference)
        if not match:
            raise ProviderError(
                f"Invalid reference format: {reference}",
                provider=self.info.name,
                reference=reference,
            )

        service = match.group("service")
        secret_name = match.group("secret")

        # Fetch the secret from your service
        # This is where you'd call your API
        try:
            value = await self._fetch_from_api(service, secret_name)
        except Exception as exc:
            raise ProviderError(
                f"Failed to fetch secret: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        return value

    async def _fetch_from_api(self, service: str, secret_name: str) -> str:
        """Actually fetch the secret from your service."""
        # Implementation here
        return "secret_value"
```

### Step 2: Register the Provider

Option A: Register programmatically

```python
# In your application startup
from my_provider import MyCustomProvider
ProviderRegistry.register(MyCustomProvider)
```

Option B: Register as a plugin entry point

```python
# In your package's pyproject.toml
[project.entry-points."use_env.providers"]
my_custom = "my_provider:MyCustomProvider"
```

Option C: Register in configuration

```yaml
# .use-env.yaml
providers:
  - name: my_custom
    type: my_custom
    enabled: true
```

### Step 3: Use the Provider

```bash
# In your .env file
MY_SECRET=${my_custom:my-service/api-key}
```

## Advanced Provider Features

### Custom Validation

Override `validate_reference` for custom validation logic:

```python
class MyProvider(Provider):
    info = ProviderInfo(
        name="my_provider",
        description="My provider",
        reference_pattern=r"^[a-z]+$",  # Basic pattern
    )

    def validate_reference(self, reference: str) -> bool:
        # Custom validation beyond regex
        if not super().validate_reference(reference):
            return False

        # Additional validation
        if reference.startswith("_"):
            raise ProviderError(
                "Secrets cannot start with underscore",
                provider=self.info.name,
                reference=reference,
            )

        return True
```

### Batch Resolution

Override `resolve_batch` for efficient batch operations:

```python
class MyProvider(Provider):
    info = ProviderInfo(name="my_provider", description="My provider")

    async def resolve_batch(
        self,
        references: list[str],
        progress_callback=None
    ) -> dict[str, str]:
        """Fetch multiple secrets in a single API call."""
        # Group references by service
        by_service: dict[str, list[str]] = {}
        for ref in references:
            service = ref.split("/")[0]
            by_service.setdefault(service, []).append(ref)

        results: dict[str, str] = {}

        for service, refs in by_service.items():
            if progress_callback:
                progress_callback(service, len(results), len(references))

            # Fetch all secrets for this service in one call
            batch_result = await self._fetch_batch(service, refs)

            for ref, value in batch_result.items():
                results[ref] = value

        return results
```

### Configuration

Support provider-specific configuration:

```python
class MyProvider(Provider):
    info = ProviderInfo(name="my_provider", description="My provider")

    def __init__(self) -> None:
        super().__init__()
        self._api_url = "https://default.example.com"
        self._timeout = 30

    def configure(self, config: dict) -> None:
        """Apply configuration from YAML."""
        if "api_url" in config:
            self._api_url = config["api_url"]
        if "timeout" in config:
            self._timeout = config["timeout"]

    async def resolve(self, reference: str) -> str:
        # Use configured values
        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(f"{self._api_url}/{reference}") as response:
                return await response.text()
```

Configuration in YAML:

```yaml
providers:
  - name: my_provider
    type: my_provider
    enabled: true
    config:
      api_url: "https://api.example.com"
      timeout: 60
```

### Resource Cleanup

Implement `close()` for cleanup:

```python
class MyProvider(Provider):
    info = ProviderInfo(name="my_provider", description="My provider")

    def __init__(self) -> None:
        super().__init__()
        self._session: aiohttp.ClientSession | None = None

    async def resolve(self, reference: str) -> str:
        if self._session is None:
            self._session = aiohttp.ClientSession()

        # Use session...
        return "value"

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
```

Use with context manager:

```python
async with ProviderRegistry.get("my_provider") as provider:
    value = await provider.resolve("secret")
# Provider is automatically closed
```

## Testing Your Provider

```python
# tests/test_my_provider.py
import pytest
from my_provider import MyProvider
from use_env.providers import ProviderError

class TestMyProvider:
    @pytest.mark.asyncio
    async def test_resolve_success(self):
        provider = MyProvider()
        value = await provider.resolve("service/secret")
        assert value == "expected_value"

    @pytest.mark.asyncio
    async def test_resolve_invalid_reference(self):
        provider = MyProvider()
        with pytest.raises(ProviderError):
            await provider.resolve("invalid-reference")

    @pytest.mark.asyncio
    async def test_validate_reference(self):
        provider = MyProvider()
        assert provider.validate_reference("valid-ref") is True
        assert provider.validate_reference("invalid") is False
```

## Best Practices

1. **Error Handling**: Always catch exceptions and raise `ProviderError`
2. **Caching**: Cache resolved values for performance
3. **Validation**: Validate references before attempting resolution
4. **Documentation**: Document the reference format in `ProviderInfo`
5. **Testing**: Write comprehensive tests
6. **Async**: Use async/await for I/O operations
7. **Cleanup**: Implement `close()` for resource cleanup
8. **Type Hints**: Add type hints for better IDE support

## Example Providers

### AWS Secrets Manager

```python
class AwsSecretsProvider(Provider):
    info = ProviderInfo(
        name="aws-secrets",
        description="AWS Secrets Manager provider",
        reference_pattern=r"^(?P<region>[^/]+)/(?P<secret_id>.+)$"
    )

    async def resolve(self, reference: str) -> str:
        import boto3
        region, secret_id = reference.split("/", 1)

        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_id)
        return response["SecretString"]
```

### HashiCorp Vault

```python
class VaultProvider(Provider):
    info = ProviderInfo(
        name="hashicorp-vault",
        description="HashiCorp Vault provider",
        reference_pattern=r"^(?P<mount>[^/]+)/(?P<path>.+)$"
    )

    async def resolve(self, reference: str) -> str:
        import hvac
        mount, path = reference.split("/", 1)

        client = hvac.Client()
        secret = client.secrets.kv.v2.read_secret_version(path=path, mount_point=mount)
        return secret["data"]["data"]["value"]
```

### 1Password

```python
class OnePasswordProvider(Provider):
    info = ProviderInfo(
        name="1password",
        description="1Password Connect provider",
        reference_pattern=r"^(?P<vault>[^/]+)/(?P<item>[^/]+)/(?P<field>.+)$"
    )

    async def resolve(self, reference: str) -> str:
        vault, item, field = reference.split("/")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._connect_url}/v1/vaults/{vault}/items/{item}/fields/{field}",
                headers={"Authorization": f"Bearer {self._token}"}
            ) as response:
                data = await response.json()
                return data["value"]
```

## Troubleshooting

### Provider Not Found

Ensure the provider is registered:

```python
from use_env.providers import ProviderRegistry

# Check if registered
print(ProviderRegistry.is_registered("my_provider"))

# List all providers
for info in ProviderRegistry.list_providers():
    print(f"{info.name}: {info.description}")
```

### Reference Not Resolving

1. Check the reference format matches your pattern
2. Verify the provider is enabled in config
3. Enable verbose output: `use-env .env.dev -v -v`

### Registration Errors

- Ensure `ProviderInfo` is defined
- Check the name is unique
- Verify `resolve()` method is implemented
