"""
Command-line interface for use-env.

This module provides the CLI entry point and argument parsing.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import yaml
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from .config import UseEnvConfig
from .loader import EnvLoader, EnvFileError
from .providers import ProviderRegistry

# Import to register built-in providers
from .providers.built_in import register_built_in_providers  # noqa: F401


def main() -> int:
    """Main entry point for the CLI."""
    try:
        return asyncio.run(_main_async())
    except KeyboardInterrupt:
        rprint("[yellow]Cancelled.[/yellow]")
        return 130
    except Exception as exc:
        rprint(f"[red]Error: {exc}[/red]")
        return 1


async def _main_async() -> int:
    """Async main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Environment file processor with secret resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  use-env .env.dev                    # Process .env.dev and output .env
  use-env .env.prod -o .env           # Output to specific file
  use-env .env.staging --strict       # Fail on any resolution errors
  use-env --list-providers            # List available providers
  use-env --config .use-env.yaml      # Use specific config file
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=".env.dev",
        help="Input environment file (default: .env.dev)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: <input_dir>/.env)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any resolution errors",
    )

    parser.add_argument(
        "--config",
        help="Configuration file path",
    )

    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List all available providers",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="use-env 1.0.0",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )

    args = parser.parse_args()

    if args.list_providers:
        _display_providers()
        return 0

    return await _process_file(
        input_path=args.input,
        output_path=args.output,
        strict=args.strict,
        config_path=args.config,
        verbose=args.verbose,
    )


def _display_providers() -> None:
    """Display all available providers."""
    providers = ProviderRegistry.list_providers()

    if not providers:
        rprint("[yellow]No providers registered.[/yellow]")
        return

    table = Table(title="Available Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Version", style="yellow")

    for provider in providers:
        table.add_row(
            provider.name,
            provider.description,
            provider.version,
        )

    rprint(table)


async def _process_file(
    input_path: str,
    output_path: str | None,
    strict: bool,
    config_path: str | None,
    verbose: int,
) -> int:
    """Process an environment file."""
    if verbose > 0:
        rprint(f"[cyan]Input file:[/cyan] {input_path}")

    config = UseEnvConfig.load(config_path)

    if output_path is None:
        output_path = str(Path(input_path).parent / ".env")

    loader = EnvLoader(config)

    try:
        result = await loader.load(
            input_path=input_path,
            output_path=output_path,
            strict=strict,
        )

        if verbose > 0:
            rprint(f"[green]Output file:[/green] {result.output_path}")
            rprint(f"[green]Variables:[/green] {result.variables_count}")
            rprint(f"[green]Secrets resolved:[/green] {result.secrets_resolved}")

        if result.errors:
            for error in result.errors:
                rprint(f"[yellow]Warning:[/yellow] {error.message} (key: {error.key})")

        rprint(
            f"[green]Wrote {result.output_path} with {result.secrets_resolved} secret(s) resolved.[/green]"
        )

    except EnvFileError as exc:
        rprint(f"[red]Error: {exc}[/red]")
        return 1
    except Exception as exc:
        rprint(f"[red]Error: {exc}[/red]")
        return 1
    finally:
        await loader.close()

    return 0


def _display_config(config: UseEnvConfig) -> None:
    """Display configuration."""
    rprint(Panel.fit(yaml.dump(config.__dict__, default_flow_style=False), title="Configuration"))
