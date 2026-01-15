# Architecture Documentation

This document describes the internal architecture of `use-env`.

## Overview

`use-env` is built around a plugin-based architecture where secret resolution is handled by **providers**. The core engine handles file parsing and orchestration, while providers handle the actual secret retrieval.

## Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         use-env CLI                              │
│                      (use_env.cli:main)                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                          EnvLoader                              │
│                 (use_env.loader.EnvLoader)                      │
│  • Parses .env files                                             │
│  • Finds secret references                                       │
│  • Orchestrates provider resolution                              │
│  • Writes resolved output                                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ProviderRegistry                           │
│               (use_env.providers.ProviderRegistry)              │
│  • Registers provider classes                                    │
│  • Manages provider instances                                    │
│  • Discovers plugins                                             │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────┴────────────┐
                    │      Providers          │
                    ├─────────────────────────┤
                    │ • vault (Azure KV)      │
                    │ • env (Environment)     │
                    │ • file (Filesystem)     │
                    │ + Custom providers      │
                    └─────────────────────────┘
```

## Module Structure

```
use_env/
├── __init__.py           # Main package exports
├── cli.py                # CLI entry point and argument parsing
├── config.py             # Configuration loading and parsing
├── loader.py             # Environment file loading and resolution
└── providers/
    ├── __init__.py       # Provider interface and registry
    ├── built_in.py       # Auto-registration of built-in providers
    ├── vault.py          # Azure Key Vault provider
    ├── env.py            # Environment variable provider
    └── file.py           # File-based provider
```

## Provider Interface

All providers must implement the `Provider` abstract base class:

```python
class Provider(ABC):
    info: ProviderInfo  # Metadata about the provider

    @abstractmethod
    async def resolve(self, reference: str) -> str:
        """Resolve a secret reference to its actual value."""

    def validate_reference(self, reference: str) -> bool:
        """Validate reference format (optional)."""

    async def resolve_batch(
        self, references: list[str], progress_callback=None
    ) -> dict[str, str]:
        """Resolve multiple references efficiently (optional)."""

    async def close(self) -> None:
        """Cleanup resources (optional)."""
```

## Reference Format

Secret references use the following format:

```bash
${<provider_name>:<reference>}
```

Examples:
- `${env:API_KEY}` - Environment variable
- `${file:/run/secrets/db_password}` - File
- `${vault:rg/my-vault/secret-name}` - Azure Key Vault
- `${custom:service/secret}` - Custom provider

## Configuration File

Configuration is loaded from `.use-env.yaml` (or specified via `--config`):

```yaml
providers:
  - name: provider_name
    type: provider_type
    enabled: true
    config:
      option1: value1

options:
  strict: true
  verbose: 1
```

## Data Flow

1. **Parse CLI arguments** (`cli.py`)
2. **Load configuration** (`config.py`)
3. **Create EnvLoader** with config
4. **Load environment file** (`loader.py`)
   - Read file content
   - Parse lines into variables
   - Find all `${...}` references
5. **Initialize providers** from registry
6. **Resolve each reference** using appropriate provider
7. **Replace references** with resolved values
8. **Write output** to `.env` file
9. **Cleanup** providers

## Error Handling

Errors are propagated through the `ProviderError` exception:

```python
class ProviderError(Exception):
    message: str
    provider: str | None
    reference: str | None
```

The `--strict` flag controls error behavior:
- **strict=True**: Fail on any resolution error
- **strict=False**: Warn and continue (use placeholder)

## Caching

Providers implement internal caching for performance:

- Cache is cleared when provider is closed
- Batch resolution can improve performance for API-based providers
- Configuration can disable caching if needed

## Thread Safety

- Providers are not thread-safe
- Each provider instance should be used from a single context
- The registry caches provider instances (use with caution in multi-threaded scenarios)

## Extension Points

1. **Custom Providers**: Implement `Provider` interface
2. **Configuration Loaders**: Extend `UseEnvConfig`
3. **Output Formatters**: Modify `EnvLoader._replace_references`
4. **CLI Commands**: Extend argument parser in `cli.py`
