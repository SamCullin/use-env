# Usage Guide

This guide covers all aspects of using `use-env` in your projects.

## Basic Usage

### Command Line

```bash
# Process .env.dev and output .env (default behavior)
use-env .env.dev

# Specify a different output file
use-env .env.prod -o .env.production

# Process and fail on any errors
use-env .env.prod --strict

# Increase verbosity
use-env .env.dev -v      # One v for info
use-env .env.dev -vv     # Two v for debug

# List all available providers
use-env --list-providers

# Use a specific configuration file
use-env .env.dev --config /path/to/config.yaml
```

### Supported File Formats

Input files should follow standard `.env` format:

```bash
# Comments start with #
EMPTY_LINE_IS_SKIPPED

KEY=value
ANOTHER_KEY="quoted value"
MULTI_WORD_KEY=word1 word2 word3

# References are replaced
API_KEY=${env:EXISTING_VAR}
DB_PASSWORD=${file:/run/secrets/db_password}
VAULT_SECRET=${vault:resource-group/keyvault/secret-name}
```

## Environment Files

### File Naming Convention

The tool doesn't enforce specific naming, but common patterns are:

```
.env               # Output file (generated)
.env.dev           # Development environment
.env.staging       # Staging environment
.env.prod          # Production environment
.env.local         # Local overrides (add to .gitignore!)
.env.test          # Test environment
```

### Git Ignore

Add the output file to `.gitignore`:

```gitignore
.env
.env.local
*.env
!template.env
```

### Example Project Structure

```
my-project/
├── .env.dev.template    # Template with references
├── .env.dev             # Generated (gitignored)
├── .env                 # Generated (gitignored)
├── .use-env.yaml        # Configuration
└── .gitignore
```

## Providers

### Built-in Providers

#### Environment Provider (`env`)

Reference existing environment variables:

```bash
# Basic usage
DATABASE_HOST=${env:DATABASE_HOST}

# Fallback to default if not set
API_URL=${env:API_URL:-https://default.example.com}
```

**Note**: The fallback syntax is not yet implemented.

#### File Provider (`file`)

Read secrets from files (Docker secrets, mounted secrets, etc.):

```bash
# Absolute path
DB_PASSWORD=${file:/run/secrets/db_password}

# Relative to current directory
API_KEY=${file:./secrets/api_key.txt}

# Docker secrets convention
POSTGRES_PASSWORD=${file:/run/secrets/POSTGRES_PASSWORD}
```

#### Vault Provider (`vault`)

Fetch secrets from Azure Key Vault:

```bash
# Format: ${vault://<resource_group>/<vault_name>/<secret_name>}
DB_PASSWORD=${vault:my-resource-group/my-keyvault/db-password}
API_KEY=${vault:prod-rg/production-vault/api-key}
```

**Requirements**:
- Azure CLI (`az`) installed
- Authenticated with `az login`
- Access to the Key Vault

### Custom Providers

See [Provider Development Guide](provider_development.md) for creating custom providers.

## Configuration

### Configuration File Location

The tool searches for configuration in this order:

1. `--config` flag
2. `.use-env.yaml` (current directory)
3. `.use-env.yml` (current directory)
4. `use-env.yaml` (current directory)
5. `use-env.yml` (current directory)
6. `~/.config/use-env.yaml` (user config)
7. `~/.use-env.yaml` (user config)

### Configuration Options

```yaml
# .use-env.yaml

# Provider configurations
providers:
  # Built-in provider with custom config
  - name: vault
    type: vault
    enabled: true
    config:
      # Provider-specific options
      subscription_id: "..."

  # Custom provider
  - name: custom
    type: my_custom_provider
    enabled: true
    config:
      option1: value1

  # Disabled provider
  - name: disabled_provider
    type: some_provider
    enabled: false

# Global options
options:
  strict: true          # Fail on any resolution error
  verbose: 0            # Verbosity level (0-2)
```

### Provider Configuration

Each provider can have its own configuration:

```yaml
providers:
  - name: file
    type: file
    enabled: true
    config:
      base_path: "/secrets"  # Base path for relative file paths
```

## Integration

### Pre-commit Hook

This repository ships a pre-configured `.pre-commit-config.yaml` that runs:

- `pyrefly check use_env/ tests/`
- `ruff check use_env/ tests/`
- `ruff format use_env/ tests/`
- `pytest`

Install the hooks locally with:

```bash
uv sync --all-extras --dev
uv tool install pre-commit
```

Every commit will now enforce type checking and lint/format consistency automatically.

### Makefile

```makefile
.env:
	use-env .env.dev

.PHONY: generate-env
generate-env: .env
```

### Docker

```dockerfile
# Build stage
FROM python:3.12-slim as builder
RUN pip install use-env

# Runtime stage
FROM python:3.12-slim
COPY --from=builder /usr/local/bin/use-env /usr/local/bin/
COPY .env.production.template /app/.env.production.template
WORKDIR /app

# Generate .env during container startup
CMD ["sh", "-c", "use-env .env.production.template -o .env && exec python app.py"]
```

### CI/CD Pipeline

#### GitHub Actions

```yaml
name: Generate Environment
on: push

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install use-env
        run: pip install use-env

      - name: Generate .env
        run: use-env .env.production
        env:
          AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
          AZURE_CLIENT_SECRET: ${{ secrets.AZURE_CLIENT_SECRET }}
          AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}

      - name: Run script with loaded creds
        run: |
          set -a
          source .env
          set +a
          ./scripts/run-with-creds.sh
```

## Best Practices

### 1. Template Files

Keep template files in version control:

```bash
# .env.dev.template (committed to git)
DATABASE_HOST=localhost
DATABASE_PORT=5432
API_KEY=${env:MY_API_KEY}  # Set in environment, throws if not found
```

### 2. Multiple Environments

```bash
# .env.dev.template
DATABASE_HOST=localhost
DEBUG=true

# .env.prod.template
DATABASE_HOST=${env:PROD_DB_HOST}
DEBUG=false
DATABASE_PASSWORD=${vault:prod-rg/prod-vault/db-password}
```

### 3. Security

- Never commit `.env` files
- Use `.env.template` or `.env.example` for templates
- Rotate secrets regularly
- Use least-privilege access for providers

### 4. Error Handling

```bash
# Strict mode - fails on any error
use-env .env.prod --strict

# Lenient mode - warns but continues
use-env .env.dev
```

### 5. Debugging

```bash
# Maximum verbosity
use-env .env.dev -vvv

# List providers with details
use-env --list-providers --verbose
```

## Troubleshooting

### Azure CLI Not Found

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version
```

### Provider Not Found

```bash
# List available providers
use-env --list-providers

# Check configuration
cat .use-env.yaml
```

### Permission Denied (File Provider)

```bash
# Check file permissions
ls -la /run/secrets/

# Fix permissions (if running as root)
sudo chmod 644 /run/secrets/*
```

### Reference Not Resolved

1. Check reference syntax matches provider format
2. Verify the secret exists in the source
3. Enable verbose mode: `use-env .env.dev -v`

### Slow Resolution

For many secrets, batch resolution is faster:

```bash
# Group references for efficient fetching
DB_HOST=${vault:rg/vault/host}
DB_PASS=${vault:rg/vault/pass}
# These will be fetched in parallel
```
