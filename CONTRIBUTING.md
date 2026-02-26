# Contributing to use-env

Thank you for your interest in contributing! This document outlines the guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch

## Development Setup

```bash
# Clone and install
git clone https://github.com/YOUR_USERNAME/use-env.git
cd use-env
uv sync --all-extras --dev

# Run tests
pytest

# Run linters
pyrefly check use_env/ tests/
ruff check use_env/ tests/
ruff format use_env/ tests/
```

## Commit Message Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/) for automatic versioning and changelog generation.

### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that do not affect the meaning of the code (white-space, formatting, etc)
- **refactor**: A code change that neither fixes a bug nor adds a feature
- **perf**: A code change that improves performance
- **test**: Adding missing tests or correcting existing tests
- **chore**: Changes to the build process or auxiliary tools

### Examples

```
feat: add AWS Secrets Manager provider

fix: resolve environment variable caching issue

docs: update installation instructions

refactor: improve provider registry lookup performance

BREAKING CHANGE: the provider interface has been updated
```

### Breaking Changes

Breaking changes must be indicated by:
1. Starting the footer with `BREAKING CHANGE:`
2. Using a `!` after the type/scope

```
feat!: remove deprecated vault CLI provider

BREAKING CHANGE: The vault CLI provider has been removed.
Use the azure-keyvault provider instead.
```

## Pull Requests

1. Ensure all tests pass
2. Ensure linting passes
3. Update documentation if needed
4. Add tests for new features
5. Keep commits atomic and properly formatted

## Release Process

Releases are automatically handled by [python-semantic-release](https://python-semantic-release.readthedocs.io/).

When a PR is merged to main:
1. Semantic release analyzes commits
2. Version is bumped according to commit messages
3. Changelog is generated
4. GitHub release is created
5. Package is published to PyPI

## Code Style

- Follow PEP 8 (enforced by ruff)
- Add type hints to all functions
- Write docstrings for public APIs
- Keep functions small and focused

## Testing

All new features should include tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=use_env --cov-report=xml
```
