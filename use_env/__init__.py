"""
use-env: Environment file processor with extensible secret providers.

This tool allows developers to define environment files with secret references
that can be resolved from various providers (vault, environment variables, files, etc.).

Basic Usage:
    use-env .env.dev

For more information, see:
    https://github.com/yourusername/use-env
"""

from .cli import main
from .config import UseEnvConfig
from .loader import EnvLoader
from .providers import Provider, ProviderRegistry, ProviderError

__version__ = "1.0.0"
__all__ = [
    "main",
    "UseEnvConfig",
    "EnvLoader",
    "Provider",
    "ProviderRegistry",
    "ProviderError",
]
