"""
File-based provider for use-env.

This module provides a provider that reads secret values from files.
Useful for Docker secrets, mounted files, or any file-based secret storage.

Reference Format:
    ${file:/path/to/secret.txt}
    ${file://relative/path.txt}

Example:
    DATABASE_PASSWORD=${file:/run/secrets/db_password}
    API_KEY=${file:./secrets/api_key.txt}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class FileProvider(Provider):
    """
    File-based secret provider.

    Reads secret values from files on the filesystem.
    Useful for Docker secrets, mounted Kubernetes secrets, or local files.

    Configuration:
        base_path: Base directory for relative paths (default: current directory)
        required: Whether files must exist (default: True)

    Example:
        # In your .env.dev file:
        DB_PASSWORD=${file:/run/secrets/db_password}
        API_KEY=${file:./secrets/api_key.txt}
    """

    info = ProviderInfo(
        name="file",
        description="File-based secret provider",
        version="1.0.0",
        author="use-env contributors",
        reference_pattern=r"^(?P<path>.+)$",
    )

    def __init__(self, base_path: str | None = None) -> None:
        super().__init__()
        self._base_path = Path(base_path) if base_path else Path.cwd()
        self._cache: dict[str, str] = {}

    async def resolve(self, reference: str) -> str:
        """
        Read a secret from a file.

        Args:
            reference: Path to the file containing the secret

        Returns:
            The contents of the file (stripped of whitespace)

        Raises:
            ProviderError: If the file cannot be read
        """
        # Check cache first
        if reference in self._cache:
            return self._cache[reference]

        # Resolve the path
        file_path = self._resolve_path(reference)

        # Read the file
        try:
            value = file_path.read_text().strip()
        except FileNotFoundError as exc:
            raise ProviderError(
                f"Secret file not found: {file_path}",
                provider=self.info.name,
                reference=reference,
            ) from exc
        except PermissionError as exc:
            raise ProviderError(
                f"Permission denied reading secret file: {file_path}",
                provider=self.info.name,
                reference=reference,
            ) from exc
        except OSError as exc:
            raise ProviderError(
                f"Error reading secret file {file_path}: {exc}",
                provider=self.info.name,
                reference=reference,
            ) from exc

        # Cache the result
        self._cache[reference] = value

        return value

    def _resolve_path(self, reference: str) -> Path:
        """Resolve a file path from the reference."""
        # Handle file:// prefix
        if reference.startswith("file://"):
            reference = reference[7:]

        path = Path(reference)

        # Make relative paths relative to base_path
        if not path.is_absolute():
            path = self._base_path / path

        return path

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the file provider with options."""
        if "base_path" in config:
            self._base_path = Path(config["base_path"])

    async def close(self) -> None:
        """Clean up resources."""
        self._cache.clear()

    async def resolve_batch(
        self, references: list[str], progress_callback: Any | None = None
    ) -> dict[str, str]:
        """Resolve multiple files efficiently."""
        results: dict[str, str] = {}

        for i, ref in enumerate(references):
            if progress_callback:
                progress_callback(ref, i, len(references))

            results[ref] = await self.resolve(ref)

        return results


def create_provider(base_path: str | None = None) -> FileProvider:
    """Factory function to create a FileProvider instance."""
    return FileProvider(base_path)
