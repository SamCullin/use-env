"""
Tests for the provider interface and registry.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

from use_env.providers import (
    Provider,
    ProviderInfo,
    ProviderRegistry,
    ProviderError,
    ResolutionResult,
)


class TestProviderInfo:
    """Tests for ProviderInfo dataclass."""

    def test_create_provider_info(self):
        """Test creating a ProviderInfo instance."""
        info = ProviderInfo(
            name="test",
            description="A test provider",
            version="1.0.0",
        )

        assert info.name == "test"
        assert info.description == "A test provider"
        assert info.version == "1.0.0"
        assert info.author == ""
        assert info.reference_pattern == ""


class TestProvider:
    """Tests for the base Provider class."""

    def test_abstract_resolve(self):
        """Test that Provider is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            Provider()

    @pytest_asyncio.fixture
    async def mock_provider(self):
        """Create a mock provider for testing."""

        class TestProvider(Provider):
            info = ProviderInfo(
                name="test",
                description="A test provider",
                reference_pattern=r"^(?P<value>.+)$",
            )

            async def resolve(self, reference: str) -> str:
                return f"resolved:{reference}"

        return TestProvider()

    @pytest.mark.asyncio
    async def test_validate_reference_with_pattern(self, mock_provider):
        """Test reference validation with a pattern."""
        assert mock_provider.validate_reference("valid_value") is True
        assert mock_provider.validate_reference("another-value") is True

    @pytest.mark.asyncio
    async def test_validate_reference_without_pattern(self):
        """Test reference validation without a pattern."""

        class NoPatternProvider(Provider):
            info = ProviderInfo(
                name="nopattern",
                description="No pattern provider",
            )

            async def resolve(self, reference: str) -> str:
                return reference

        provider = NoPatternProvider()
        assert provider.validate_reference("any_value") is True

    @pytest.mark.asyncio
    async def test_resolve_batch(self, mock_provider):
        """Test batch resolution."""
        references = ["ref1", "ref2", "ref3"]
        results = await mock_provider.resolve_batch(references)

        assert len(results) == 3
        assert results["ref1"] == "resolved:ref1"
        assert results["ref2"] == "resolved:ref2"
        assert results["ref3"] == "resolved:ref3"


class TestProviderRegistry:
    """Tests for the ProviderRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        ProviderRegistry.clear()

    def teardown_method(self):
        """Clear registry after each test."""
        ProviderRegistry.clear()

    def test_register_provider(self):
        """Test registering a provider."""

        class TestProvider(Provider):
            info = ProviderInfo(name="test", description="Test")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(TestProvider)
        assert ProviderRegistry.is_registered("test")

    def test_register_provider_with_custom_name(self):
        """Test registering a provider with a custom name."""

        class CustomProvider(Provider):
            info = ProviderInfo(name="original", description="Custom")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(CustomProvider, name="custom")
        assert ProviderRegistry.is_registered("custom")
        assert not ProviderRegistry.is_registered("original")

    def test_register_duplicate_raises_error(self):
        """Test that registering a duplicate provider raises an error."""

        class DuplicateProvider(Provider):
            info = ProviderInfo(name="dup", description="Duplicate")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(DuplicateProvider)

        with pytest.raises(KeyError):
            ProviderRegistry.register(DuplicateProvider)

    def test_register_without_info_raises_error(self):
        """Test that registering a provider without info raises an error."""

        class NoInfoProvider(Provider):
            async def resolve(self, reference: str) -> str:
                return reference

        with pytest.raises(ValueError):
            ProviderRegistry.register(NoInfoProvider)

    def test_get_provider(self):
        """Test getting a provider instance."""

        class TestProvider(Provider):
            info = ProviderInfo(name="test", description="Test")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(TestProvider)
        instance = ProviderRegistry.get("test")

        assert instance is not None
        assert isinstance(instance, TestProvider)

    def test_get_unknown_provider_raises_error(self):
        """Test that getting an unknown provider raises an error."""
        with pytest.raises(KeyError):
            ProviderRegistry.get("unknown")

    def test_list_providers(self):
        """Test listing all providers."""

        class Provider1(Provider):
            info = ProviderInfo(name="p1", description="Provider 1")

            async def resolve(self, reference: str) -> str:
                return reference

        class Provider2(Provider):
            info = ProviderInfo(name="p2", description="Provider 2")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(Provider1)
        ProviderRegistry.register(Provider2)

        providers = ProviderRegistry.list_providers()

        assert len(providers) == 2
        names = {p.name for p in providers}
        assert names == {"p1", "p2"}

    def test_provider_caching(self):
        """Test that provider instances are cached."""

        class TestProvider(Provider):
            info = ProviderInfo(name="test", description="Test")

            async def resolve(self, reference: str) -> str:
                return reference

        ProviderRegistry.register(TestProvider)

        instance1 = ProviderRegistry.get("test")
        instance2 = ProviderRegistry.get("test")

        assert instance1 is instance2


class TestProviderError:
    """Tests for ProviderError exception."""

    def test_error_with_all_details(self):
        """Test creating an error with all details."""
        error = ProviderError(
            "Something went wrong",
            provider="test",
            reference="ref123",
        )

        assert error.message == "Something went wrong"
        assert error.provider == "test"
        assert error.reference == "ref123"
        assert "[test]" in str(error)
        assert "ref123" in str(error)

    def test_error_without_details(self):
        """Test creating an error without details."""
        error = ProviderError("Simple error")

        assert error.message == "Simple error"
        assert error.provider is None
        assert error.reference is None

    def test_error_str_format(self):
        """Test error string formatting."""
        error = ProviderError(
            "Failed to resolve",
            provider="vault",
            reference="rg/vault/secret",
        )

        error_str = str(error)
        assert "[vault]" in error_str
        assert "Failed to resolve" in error_str
        assert "rg/vault/secret" in error_str
