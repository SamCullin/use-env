"""
Tests for the file-based provider.
"""

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from use_env.providers.file import FileProvider
from use_env.providers import ProviderError


class TestFileProvider:
    """Tests for the FileProvider class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def secret_file(self, temp_dir):
        """Create a test secret file."""
        secret_path = temp_dir / "secret.txt"
        secret_path.write_text("super_secret_value")
        return secret_path

    @pytest.mark.asyncio
    async def test_read_secret_file(self, secret_file):
        """Test reading a secret from a file."""
        provider = FileProvider()

        result = await provider.resolve(str(secret_file))

        assert result == "super_secret_value"

    @pytest.mark.asyncio
    async def test_read_with_file_prefix(self, secret_file):
        """Test reading a file with file:// prefix."""
        provider = FileProvider()

        result = await provider.resolve(f"file://{secret_file}")

        assert result == "super_secret_value"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file_raises_error(self, temp_dir):
        """Test that reading a nonexistent file raises an error."""
        provider = FileProvider()
        nonexistent = temp_dir / "nonexistent.txt"

        with pytest.raises(ProviderError) as exc_info:
            await provider.resolve(str(nonexistent))

        assert "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_relative_path_with_base(self, temp_dir):
        """Test reading a relative path with base directory."""
        # Create a file in the temp directory
        (temp_dir / "mysecret").write_text("relative_secret")

        provider = FileProvider(base_path=str(temp_dir))

        result = await provider.resolve("mysecret")

        assert result == "relative_secret"

    @pytest.mark.asyncio
    async def test_caching(self, secret_file):
        """Test that values are cached."""
        provider = FileProvider()

        result1 = await provider.resolve(str(secret_file))

        # Modify the file
        secret_file.write_text("modified_secret")

        # Second resolve should return cached value
        result2 = await provider.resolve(str(secret_file))

        assert result1 == "super_secret_value"
        assert result2 == "super_secret_value"

    @pytest.mark.asyncio
    async def test_close_clears_cache(self, secret_file):
        """Test that close clears the cache."""
        provider = FileProvider()

        await provider.resolve(str(secret_file))
        await provider.close()

        secret_file.write_text("new_secret")
        result = await provider.resolve(str(secret_file))

        assert result == "new_secret"

    @pytest.mark.asyncio
    async def test_strips_whitespace(self, temp_dir):
        """Test that whitespace is stripped from file contents."""
        file_path = temp_dir / "whitespace.txt"
        file_path.write_text("  secret with spaces  \n\t")

        provider = FileProvider()
        result = await provider.resolve(str(file_path))

        assert result == "secret with spaces"

    @pytest.mark.asyncio
    async def test_permission_error(self, temp_dir):
        """Test handling of permission errors."""
        if os.name == "nt":
            pytest.skip("Permission tests not applicable on Windows")

        file_path = temp_dir / "no_permission.txt"
        file_path.write_text("secret")
        os.chmod(str(file_path), 0o000)

        try:
            provider = FileProvider()
            with pytest.raises(ProviderError) as exc_info:
                await provider.resolve(str(file_path))
            assert "permission" in str(exc_info.value).lower()
        finally:
            os.chmod(str(file_path), 0o644)


import os
