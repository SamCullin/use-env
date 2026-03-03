"""
Command-line interface for use-env.

This module provides the CLI entry point and argument parsing.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import yaml
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from .config import UseEnvConfig
from .loader import EnvFileError, EnvLoader
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


def _is_piped() -> bool:
    """Check if stdout is a pipe (piping to another command)."""
    return not os.isatty(sys.stdout.fileno())


def _has_stdin() -> bool:
    """Check if stdin has data (for piping)."""
    return not sys.stdin.isatty()


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
  cat .env.dev | use-env              # Pipe input, output to stdout
  cat .env.dev | use-env > .env       # Pipe input, save output to .env
  use-env .env.dev | grep DB_HOST     # Pipe output to another command
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Input environment file (default: .env.dev, or stdin if piped)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: <input_dir>/.env, or stdout if piped)",
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

    # Determine if we're in piped mode
    is_piped = _is_piped()
    has_stdin = _has_stdin()

    # Handle input source
    if args.input == "-":
        # Explicit stdin
        input_source = "stdin"
    elif args.input is None:
        if has_stdin:
            # Piped input
            input_source = "stdin"
        else:
            # Default file
            args.input = ".env.dev"
            input_source = str(Path(args.input).resolve())
    else:
        input_source = str(Path(args.input).resolve())

    # Handle output destination
    if args.output == "-":
        # Explicit stdout
        output_to_stdout = True
    elif is_piped:
        # Piped output
        output_to_stdout = True
    elif args.output is None:
        # Default: file next to input or .env in current directory
        # BUT if input is from stdin, output to stdout
        if input_source == "stdin":
            output_to_stdout = True
        elif args.input:
            input_path = Path(args.input)
            if input_path.is_absolute() or input_path.exists():
                args.output = str(input_path.parent / ".env")
            else:
                args.output = ".env"
            output_to_stdout = False
        else:
            args.output = ".env"
            output_to_stdout = False
    else:
        output_to_stdout = False

    return await _process_file(
        input_source=input_source,
        input_path=args.input,
        output_path=args.output,
        output_to_stdout=output_to_stdout,
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
    input_source: str,
    input_path: str | None,
    output_path: str | None,
    output_to_stdout: bool,
    strict: bool,
    config_path: str | None,
    verbose: int,
) -> int:
    """Process an environment file."""

    if verbose > 0:
        rprint(f"[cyan]Input source:[/cyan] {input_source}")

    config = UseEnvConfig.load(config_path)

    # Determine output path
    if output_to_stdout:
        final_output_path = "-"
    elif output_path is None:
        if input_path:
            input_file = Path(input_path)
            final_output_path = str(input_file.parent / ".env")
        else:
            final_output_path = ".env"
    else:
        final_output_path = output_path

    loader = EnvLoader(config)

    try:
        # Read from stdin if needed
        stdin_content: str | None = None
        if input_source == "stdin":
            stdin_content = sys.stdin.read()

        result = await loader.load(
            input_path=input_path,
            output_path=final_output_path,
            strict=strict,
            stdin_content=stdin_content,
        )

        if verbose > 0:
            if output_to_stdout:
                rprint("[green]Output:[/green] stdout")
            else:
                rprint(f"[green]Output file:[/green] {result.output_path}")
            rprint(f"[green]Variables:[/green] {result.variables_count}")
            rprint(f"[green]Secrets resolved:[/green] {result.secrets_resolved}")

        # Output to stdout if requested
        if output_to_stdout:
            sys.stdout.write(result.resolved_content)
            sys.stdout.flush()

        if result.errors:
            for error in result.errors:
                rprint(f"[yellow]Warning:[/yellow] {error.message} (key: {error.key})")

        if not output_to_stdout:
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
