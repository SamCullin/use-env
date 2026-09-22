"""Tests for the shell provider."""

import pytest

from use_env.providers import ProviderError
from use_env.providers.shell import ShellProvider


class TestShellProvider:
    """Test shell command execution and error handling."""

    @pytest.mark.asyncio
    async def test_resolve_returns_trimmed_stdout(self):
        provider = ShellProvider()

        result = await provider.resolve('printf "  Hello\\n"')

        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_failed_command_raises_provider_error(self):
        provider = ShellProvider()

        with pytest.raises(ProviderError, match="exit code 7"):
            await provider.resolve("exit 7")

    @pytest.mark.asyncio
    async def test_empty_command_raises_provider_error(self):
        provider = ShellProvider()

        with pytest.raises(ProviderError, match="cannot be empty"):
            await provider.resolve("   ")

    def test_configure_timeout(self):
        provider = ShellProvider()

        provider.configure({"timeout": 5})

        assert provider._timeout == 5

    def test_configure_rejects_invalid_timeout(self):
        provider = ShellProvider()

        with pytest.raises(ValueError, match="positive number"):
            provider.configure({"timeout": 0})
