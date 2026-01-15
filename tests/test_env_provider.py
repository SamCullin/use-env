"""
Tests for the environment variable provider.
"""

import pytest
import pytest_asyncio
import os

from use_env.providers.env import EnvironmentProvider
from use_env.providers import ProviderError


class TestEnvironmentProvider:
    """Tests for the EnvironmentProvider class."""

    def setup_method(self):
        """Set up test environment variables."""
        os.environ["TEST_VAR"] = "test_value"
        os.environ["ANOTHER_VAR"] = "another_value"

    def teardown_method(self):
        """Clean up test environment variables."""
        os.environ.pop("TEST_VAR", None)
        os.environ.pop("ANOTHER_VAR", None)
        os.environ.pop("MISSING_VAR", None)

    @pytest.mark.asyncio
    async def test_resolve_existing_variable(self):
        """Test resolving an existing environment variable."""
        provider = EnvironmentProvider()

        result = await provider.resolve("TEST_VAR")

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_resolve_with_env_prefix(self):
        """Test resolving with env: prefix."""
        provider = EnvironmentProvider()

        result = await provider.resolve("env:TEST_VAR")

        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_resolve_missing_variable_raises_error(self):
        """Test that resolving a missing variable raises an error."""
        provider = EnvironmentProvider()

        with pytest.raises(ProviderError) as exc_info:
            await provider.resolve("MISSING_VAR")

        assert "MISSING_VAR" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_reference_format(self):
        """Test that invalid reference format raises an error."""
        provider = EnvironmentProvider()

        with pytest.raises(ProviderError):
            await provider.resolve("123invalid")

    @pytest.mark.asyncio
    async def test_caching(self):
        """Test that values are cached."""
        provider = EnvironmentProvider()

        # First resolve
        result1 = await provider.resolve("TEST_VAR")

        # Modify the environment
        os.environ["TEST_VAR"] = "modified_value"

        # Second resolve should return cached value
        result2 = await provider.resolve("TEST_VAR")

        assert result1 == "test_value"
        assert result2 == "test_value"

        # Clean up
        await provider.close()

    @pytest.mark.asyncio
    async def test_close_clears_cache(self):
        """Test that close clears the cache."""
        provider = EnvironmentProvider()

        await provider.resolve("TEST_VAR")
        await provider.close()

        os.environ["TEST_VAR"] = "new_value"
        result = await provider.resolve("TEST_VAR")

        assert result == "new_value"
