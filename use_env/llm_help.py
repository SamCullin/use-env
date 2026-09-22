"""Detailed, plain-text help for language-model-assisted use of use-env."""

LLM_HELP_TEXT = """use-env — detailed usage guide

Purpose
=======
use-env processes a dotenv-style input file and replaces secret references with values from registered providers. It writes a generated .env file by default, or writes the resolved content to stdout when input or output is piped.

Command shape
=============
use-env [INPUT] [-o OUTPUT] [OPTIONS]

Input and output
================
- INPUT is an environment file. If omitted, use-env reads .env.dev unless stdin is piped.
- Use INPUT=- to force stdin.
- OUTPUT defaults to <input-directory>/.env for a terminal invocation.
- Use -o PATH to choose an output file.
- Use -o - to force stdout. Piped invocations also write to stdout.
- Comments, blank lines, ordinary KEY=value entries, and quoted values are preserved.

Reference syntax
================
Provider references use ${provider:reference}:

  API_KEY=${env:API_KEY}
  PASSWORD=${file:/run/secrets/database-password}

The shell shorthand executes a command and replaces the reference with trimmed stdout:

  GREETING=${! echo "Hello" }

The equivalent provider form is:

  GREETING=${shell:echo "Hello"}

Shell commands run through the current system shell, inherit the current working directory and environment, and execute concurrently with other references. A non-zero exit status, an empty command, or a command running longer than the configured timeout is a resolution error. The default shell timeout is 30 seconds.

Shell references execute arbitrary commands with the permissions of the use-env process. Only process trusted input files, and do not place untrusted values directly into a shell reference. Command output can contain secrets and may be written to the generated .env file.

Built-in providers
==================
- env: read an existing environment variable, for example ${env:DATABASE_URL}.
- file: read and trim a local file, for example ${file:/run/secrets/database-password}.
- shell: execute a shell command, using either ${! command } or ${shell:command}.
- Optional cloud providers are available when their extras are installed; use --list-providers to inspect the current installation.

Useful options
==============
- --help: show concise command-line help and examples.
- --llm-help: show this detailed, machine-readable usage guide.
- --list-providers: list registered providers.
- --provider-help PROVIDER: show provider-specific setup and security guidance.
- --config PATH: load a specific YAML configuration file.
- --strict: fail with exit status 1 on the first resolution error.
- --verbose, -v: show processing details; repeat the flag for a higher verbosity level.
- --version: show the installed use-env version.

Shell provider configuration
============================
Set a timeout in seconds through .use-env.yaml when a command needs a different limit:

  providers:
    - name: shell
      type: shell
      config:
        timeout: 10

The provider name must remain shell when using ${shell:...} or the ! shorthand.

Examples
========
1. Resolve a template to .env:
   use-env .env.dev

2. Resolve stdin to stdout:
   printf 'GREETING=${! echo "Hello"}\n' | use-env

3. Fail instead of preserving unresolved references:
   use-env .env.prod --strict

4. Inspect installed providers and detailed provider help:
   use-env --list-providers
   use-env --provider-help shell

Exit status
===========
0 means the requested operation completed. 1 means input, configuration, provider, or resolution processing failed. 130 means the operation was cancelled with Ctrl-C.
"""
