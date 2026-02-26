# use-env

[![Build & Release](https://github.com/SamCullin/use-env/actions/workflows/publish.yml/badge.svg)](https://github.com/SamCullin/use-env/actions/workflows/publish.yml)
[![CI](https://github.com/SamCullin/use-env/actions/workflows/ci.yml/badge.svg)](https://github.com/SamCullin/use-env/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/use-env.svg)](https://badge.fury.io/py/use-env)
[![GitHub Release](https://img.shields.io/github/v/release/SamCullin/use-env)](https://github.com/SamCullin/use-env/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/SamCullin/use-env/graphs/commit-activity)
[![Downloads](https://img.shields.io/pypi/dm/use-env.svg)](https://pypi.org/project/use-env/)
[![GitHub issues](https://img.shields.io/github/issues/SamCullin/use-env.svg)](https://github.com/SamCullin/use-env/issues)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://makeapullrequest.com)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)

[use-env](/) > [use_env](/use_env/) > [providers](/use_env/providers/) > [tests](/tests/) > [.github](/.github/) > [docs](/docs/) > [examples](/examples/)

[!['Buy Me A Coffee'](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/samcullin)

## Summary
**Environment file processor with extensible secret providers.**


`use-env` is a CLI tool for developers that processes environment files with secret references and resolves them from various providers (vault, environment variables, files, etc.).

## Features

- **Extensible Provider System**: Add custom providers for any secret source
- **Built-in Providers**: Support for environment variables and files (no external dependencies)
- **Optional Cloud Providers**: Azure, AWS, GCP, HashiCorp Vault, 1Password (install only what you need)
- **Configuration**: YAML-based configuration for custom providers
- **Type Safety**: Written in Python with full type annotations
- **Test Coverage**: Comprehensive test suite

## Installation

```bash
# Core package only (env and file providers)
pip install use-env

# Or using uv
uv pip install use-env
```

### Optional Cloud Providers

Install only the providers you need:

```bash
# Azure Key Vault (Python SDK)
pip install use-env[azure]

# AWS Secrets Manager
pip install use-env[aws]

# Google Cloud Secret Manager
pip install use-env[gcp]

# HashiCorp Vault
pip install use-env[vault]

# 1Password Connect
pip install use-env[1password]

# All cloud providers
pip install use-env[all]
```

## Quick Start

### Basic Usage

```bash
# Process .env.dev and output .env
use-env .env.dev

# Specify output file
use-env .env.prod -o .env.production

# List available providers
use-env --list-providers
```

### Environment File Example

Create a `.env.dev` file:

```bash
# Regular values
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Environment variable reference
API_KEY=${env:MY_API_KEY}

# File-based secret (Docker secrets, etc.)
DB_PASSWORD=${file:/run/secrets/db_password}

# Azure Key Vault (requires use-env[azure])
# Format: ${azure-keyvault:<vault_name>/<secret_name>}
SECRET_KEY=${azure-keyvault:my-keyvault/db-password}

# AWS Secrets Manager (requires use-env[aws])
# Format: ${aws-secrets:<region>/<secret_name>}
DB_PASSWORD=${aws-secrets:us-east-1/my-app/database}

# GCP Secret Manager (requires use-env[gcp])
# Format: ${gcp-secrets:<project_id>/<secret_name>}
API_KEY=${gcp-secrets:my-project/api-key}

# HashiCorp Vault (requires use-env[vault])
# Format: ${vault:<mount_point>/<path>}
DB_PASSWORD=${vault:secret/my-app/database}

# 1Password (requires use-env[1password])
# Format: ${1password:<vault_id>/<item_id>/<field>}
API_KEY=${1password:vault-id/item-id/api-key}
```

Run the tool:

```bash
use-env .env.dev
```

This will create a `.env` file with all references resolved.

### Piping Support

The tool supports piping for flexible workflows:

```bash
# Pipe input from stdin, output to stdout
cat .env.dev | use-env

# Pipe input, save output to file
cat .env.dev | use-env > .env

# Pipe output to another command
use-env .env.prod | grep DB_HOST

# Chain with other tools
cat .env.staging | use-env | jq '.DATABASE_'
```

When input comes from stdin, output automatically goes to stdout. This enables standard Unix workflows.

## Core Providers (No Extra Dependencies)

### Environment Provider (`env`)

Reference environment variables:

```bash
API_KEY=${env:API_KEY}
```

### File Provider (`file`)

Read secrets from files:

```bash
# Absolute path
DB_PASSWORD=${file:/run/secrets/db_password}

# Relative path (relative to config or current directory)
API_KEY=${file:./secrets/api_key.txt}
```

## Optional Cloud Providers

### Azure Key Vault (`azure-keyvault`)

Requires: `pip install use-env[azure]`

```bash
# Format: ${azure-keyvault:<vault_name>/<secret_name>}
DB_PASSWORD=${azure-keyvault:my-keyvault/db-password}
```

Configuration (in `.use-env.yaml`):

```yaml
providers:
  - name: azure
    type: azure-keyvault
    enabled: true
    config:
      tenant_id: "your-tenant-id"  # Optional, uses default credential
      client_id: "your-client-id"  # Optional
      client_secret: "your-secret" # Optional
```

### AWS Secrets Manager (`aws-secrets`)

Requires: `pip install use-env[aws]`

```bash
# Format: ${aws-secrets:<region>/<secret_name>}
DB_PASSWORD=${aws-secrets:us-east-1/my-app/database}
```

Configuration:

```yaml
providers:
  - name: aws
    type: aws-secrets
    enabled: true
    config:
      region: "us-east-1"           # Optional, uses default session
      profile: "my-aws-profile"     # Optional
```

### GCP Secret Manager (`gcp-secrets`)

Requires: `pip install use-env[gcp]`

```bash
# Format: ${gcp-secrets:<project_id>/<secret_name>}
API_KEY=${gcp-secrets:my-project/api-key}
```

Configuration:

```yaml
providers:
  - name: gcp
    type: gcp-secrets
    enabled: true
    config:
      project_id: "my-gcp-project"  # Optional, uses default
```

### HashiCorp Vault (`vault`)

Requires: `pip install use-env[vault]`

```bash
# Format: ${vault:<mount_point>/<path>}
DB_PASSWORD=${vault:secret/my-app/database}
DB_HOST=${vault:secret/my-app/host}  # Returns specific field if secret is JSON
```

Configuration:

```yaml
providers:
  - name: vault
    type: vault
    enabled: true
    config:
      url: "http://127.0.0.1:8200"  # Optional, uses VAULT_ADDR env var
      token: "your-vault-token"     # Optional, uses VAULT_TOKEN env var
      namespace: "your-namespace"   # Optional, for Enterprise Vault
      mount_point: "secret"         # Optional, default mount point
```

### 1Password Connect (`1password`)

Requires: `pip install use-env[1password]`

```bash
# Format: ${1password:<vault_id>/<item_id>/<field>}
API_KEY=${1password:vault-uuid/item-uuid/api-key}
```

Configuration:

```yaml
providers:
  - name: onepassword
    type: 1password
    enabled: true
    config:
      connect_url: "http://localhost:8080"  # Optional, uses OP_CONNECT_HOST
      connect_token: "your-token"           # Optional, uses OP_CONNECT_TOKEN
```

## Configuration

Create a `.use-env.yaml` file to configure providers:

```yaml
providers:
  - name: azure
    type: azure-keyvault
    enabled: true
    config:
      tenant_id: "your-tenant-id"

  - name: aws
    type: aws-secrets
    enabled: true
    config:
      region: "us-east-1"

options:
  strict: true
  verbose: 1
```

## Adding Custom Providers

See [Provider Development Guide](docs/provider_development.md) for detailed instructions.

## Documentation

- [Architecture](docs/architecture.md) - Internal design and components
- [Provider Development](docs/provider_development.md) - Guide for creating custom providers
- [Usage Guide](docs/usage.md) - Detailed usage instructions

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=use_env

# Run specific test file
pytest tests/test_providers.py
```

## CI/CD

This project uses GitHub Actions for continuous integration and deployment:

### Pull Requests
- Runs on Python 3.12 and 3.13
- Ruff linting and formatting checks
- MyPy type checking
- Pytest with coverage
- Coverage uploaded to Codecov

### Releases
- Automatically versions using [python-semantic-release](https://python-semantic-release.readthedocs.io/)
- Publishes to PyPI on version tags
- Creates GitHub releases with auto-generated changelog

### Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new provider
fix: resolve caching issue
docs: update documentation
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see LICENSE file for details.
