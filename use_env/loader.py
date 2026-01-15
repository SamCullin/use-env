"""
Environment file loader and resolver for use-env.

This module handles parsing environment files, finding secret references,
and resolving them using registered providers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import UseEnvConfig
from .providers import Provider, ProviderError, ProviderRegistry


@dataclass
class EnvVariable:
    """Represents a single environment variable from an env file."""

    key: str
    value: str
    line_number: int
    raw_value: str


@dataclass
class SecretReference:
    """Represents a secret reference in an environment file."""

    provider_name: str
    reference: str
    key: str
    start_pos: int
    end_pos: int


class EnvLoader:
    """
    Loads and processes environment files with secret references.

    This class handles:
    - Parsing .env files
    - Finding secret references
    - Resolving references using providers
    - Writing the resolved output

    Example:
        loader = EnvLoader()
        result = await loader.load("path/to/.env.dev")
        print(result.resolved_content)
    """

    # Pattern to match ${provider://reference} or ${provider:reference}
    REFERENCE_PATTERN = re.compile(
        r"\$\{(?P<provider>[a-zA-Z][a-zA-Z0-9_-]*):(?P<reference>[^}]+)\}"
    )

    def __init__(self, config: UseEnvConfig | None = None) -> None:
        """Initialize the env loader."""
        self.config = config or UseEnvConfig()
        self._providers: dict[str, Provider] = {}

    async def load(
        self,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
        strict: bool = True,
        stdin_content: str | None = None,
    ) -> LoadResult:
        """
        Load an environment file and resolve all secret references.

        Args:
            input_path: Path to the input .env file (optional if stdin_content provided)
            output_path: Optional path for the output .env file, or "-" for stdout
            strict: If True, raise on any resolution errors
            stdin_content: Content from stdin (for piped input)

        Returns:
            A LoadResult containing the resolved content and metadata
        """
        output_to_stdout = str(output_path) == "-"

        # Ensure input_path is a Path if provided
        if input_path is not None:
            input_path = Path(input_path)

        # Determine content source
        if stdin_content is not None:
            # Piped input
            content = stdin_content
            effective_input_path = Path("-")
        elif input_path is not None:
            if not input_path.exists():
                raise EnvFileError(f"Input file not found: {input_path}")

            content = input_path.read_text()
            effective_input_path = input_path
        else:
            raise EnvFileError("Either input_path or stdin_content must be provided")

        # Determine output path
        if output_to_stdout:
            final_output_path = Path("-")
        elif output_path is None:
            if input_path:
                final_output_path = input_path.parent / ".env"
            else:
                final_output_path = Path(".env")
        else:
            final_output_path = Path(output_path)

        lines = content.splitlines()
        variables = self._parse_lines(lines)

        references = self._find_references(content, variables)

        await self._initialize_providers()

        resolved_values: dict[str, str] = {}
        errors: list[ResolutionError] = []

        for ref in references:
            try:
                value = await self._resolve_reference(ref)
                resolved_values[f"{ref.provider_name}://{ref.reference}"] = value
            except ProviderError as exc:
                error = ResolutionError(
                    key=ref.key,
                    provider=ref.provider_name,
                    reference=ref.reference,
                    message=str(exc),
                )
                if strict:
                    raise EnvFileError(f"Failed to resolve {ref.key}: {exc}") from exc
                errors.append(error)

        if errors and strict:
            raise EnvFileError(f"Encountered {len(errors)} error(s) while resolving secrets")

        resolved_content = self._replace_references(content, resolved_values)

        # Write output
        if output_to_stdout:
            # Output handled by caller for stdout
            pass
        else:
            final_output_path.write_text(resolved_content)

        return LoadResult(
            input_path=effective_input_path,
            output_path=final_output_path,
            resolved_content=resolved_content,
            variables_count=len(variables),
            secrets_resolved=len(resolved_values),
            errors=errors,
        )

    def _parse_lines(self, lines: list[str]) -> list[EnvVariable]:
        """Parse lines into EnvVariable objects."""
        variables = []

        for line_num, line in enumerate(lines, 1):
            stripped_line = line.strip()

            if not stripped_line or stripped_line.startswith("#"):
                continue

            if "=" not in stripped_line:
                continue

            key, raw_value = stripped_line.split("=", 1)
            key = key.strip()
            raw_value = raw_value.strip()

            if (raw_value.startswith('"') and raw_value.endswith('"')) or (
                raw_value.startswith("'") and raw_value.endswith("'")
            ):
                raw_value = raw_value[1:-1]

            variables.append(
                EnvVariable(
                    key=key,
                    value=raw_value,
                    line_number=line_num,
                    raw_value=line,
                )
            )

        return variables

    def _find_references(self, content: str, variables: list[EnvVariable]) -> list[SecretReference]:
        """Find all secret references in the content."""
        references = []

        for var in variables:
            matches = self.REFERENCE_PATTERN.finditer(var.value)

            for match in matches:
                references.append(
                    SecretReference(
                        provider_name=match.group("provider"),
                        reference=match.group("reference"),
                        key=var.key,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )

        return references

    async def _initialize_providers(self) -> None:
        """Initialize all configured providers."""
        # Register providers from config
        for provider_config in self.config.providers:
            if provider_config.enabled:
                self._register_provider(provider_config)

    def _register_provider(self, config: Any) -> None:
        """Register a provider from configuration."""
        instance = ProviderRegistry.get(config.type, config.config)
        self._providers[config.name] = instance

    async def _resolve_reference(self, reference: SecretReference) -> str:
        """Resolve a single secret reference."""
        if reference.provider_name not in self._providers:
            if not ProviderRegistry.is_registered(reference.provider_name):
                raise ProviderError(
                    f"Unknown provider: {reference.provider_name}",
                    reference=reference.reference,
                )
            self._providers[reference.provider_name] = ProviderRegistry.get(reference.provider_name)

        provider = self._providers[reference.provider_name]

        if not provider.validate_reference(reference.reference):
            raise ProviderError(
                f"Invalid reference format for provider '{reference.provider_name}': {reference.reference}",
                provider=reference.provider_name,
                reference=reference.reference,
            )

        return await provider.resolve(reference.reference)

    def _replace_references(self, content: str, resolved_values: dict[str, str]) -> str:
        """Replace all secret references with their resolved values."""

        def replace_match(match: re.Match) -> str:
            provider = match.group("provider")
            reference = match.group("reference")
            key = f"{provider}://{reference}"

            return resolved_values.get(key, match.group(0))

        return self.REFERENCE_PATTERN.sub(replace_match, content)

    async def close(self) -> None:
        """Clean up all providers."""
        for provider in self._providers.values():
            await provider.close()


@dataclass
class LoadResult:
    """Result of loading an environment file."""

    input_path: Path
    output_path: Path
    resolved_content: str
    variables_count: int
    secrets_resolved: int
    errors: list[ResolutionError]


@dataclass
class ResolutionError:
    """Error that occurred during resolution."""

    key: str
    provider: str
    reference: str
    message: str


class EnvFileError(Exception):
    """Exception raised for environment file errors."""
