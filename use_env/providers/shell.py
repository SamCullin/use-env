"""Shell command provider for use-env."""

from __future__ import annotations

import asyncio
from typing import Any

from . import Provider, ProviderError, ProviderInfo


class ShellProvider(Provider):
    """Execute a shell command and return its standard output."""

    info = ProviderInfo(
        name="shell",
        description="Execute a shell command and use its standard output",
        version="1.0.0",
        author="use-env contributors",
        help="""Execute a command through the current system shell and use trimmed standard output as the resolved value.

Use `${! command }` as the shorthand syntax, or `${shell:command}` when the provider form is clearer. Commands inherit the current working directory and environment. A non-zero exit status or a timeout is treated as a resolution error.

Shell references execute arbitrary commands with the permissions of the `use-env` process. Only use them with trusted input files.""",
    )

    def __init__(self, timeout: float = 30.0) -> None:
        super().__init__()
        self._timeout = timeout

    async def resolve(self, reference: str) -> str:
        """Execute a shell command and return trimmed standard output."""
        command = reference.strip()
        if not command:
            raise ProviderError(
                "Shell command cannot be empty",
                provider=self.info.name,
                reference=reference,
            )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise ProviderError(
                f"Unable to start shell command: {exc}",
                provider=self.info.name,
                reference=command,
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), self._timeout)
        except TimeoutError as exc:
            if process.returncode is None:
                process.kill()
            await process.communicate()
            raise ProviderError(
                f"Shell command timed out after {self._timeout:g} seconds",
                provider=self.info.name,
                reference=command,
            ) from exc

        if process.returncode != 0:
            error = stderr.decode(errors="replace").strip()
            detail = f": {error}" if error else ""
            exit_code = process.returncode if process.returncode is not None else "unknown"
            raise ProviderError(
                f"Shell command failed with exit code {exit_code}{detail}",
                provider=self.info.name,
                reference=command,
            )

        return stdout.decode(errors="replace").strip()

    def validate_reference(self, reference: str) -> bool:
        """Return whether the reference contains a shell command."""
        return bool(reference.strip())

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the maximum command runtime in seconds."""
        timeout = config.get("timeout", self._timeout)
        if isinstance(timeout, bool):
            raise ValueError("Shell provider timeout must be a positive number")

        try:
            timeout_seconds = float(timeout)
        except (TypeError, ValueError) as exc:
            raise ValueError("Shell provider timeout must be a positive number") from exc

        if timeout_seconds <= 0:
            raise ValueError("Shell provider timeout must be a positive number")

        self._timeout = timeout_seconds


def create_provider(timeout: float = 30.0) -> ShellProvider:
    """Factory function for creating a shell provider."""
    return ShellProvider(timeout)
