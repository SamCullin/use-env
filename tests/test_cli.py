"""Tests for the command-line interface."""

import sys

import pytest

from use_env.cli import _main_async


class TestCLI:
    """Test command-line-only operations."""

    @pytest.mark.asyncio
    async def test_llm_help_prints_detailed_usage(self, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["use-env", "--llm-help"])

        result = await _main_async()

        output = capsys.readouterr().out
        assert result == 0
        assert "use-env — detailed usage guide" in output
        assert '${! echo "Hello" }' in output
        assert "--strict" in output
