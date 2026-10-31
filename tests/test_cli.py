"""Tests for CLI flags and helpers."""

import pytest
from click.testing import CliRunner

from readaloud.cli import main, parse_duration


def test_parse_duration():
    assert parse_duration("30s") == 30.0
    assert parse_duration("5m") == 300.0
    assert parse_duration("1h") == 3600.0
    assert parse_duration("1.5h") == 5400.0
    assert parse_duration("120") == 120.0

    with pytest.raises(Exception):
        parse_duration("invalid")


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "readaloud" in result.output


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "--speed" in result.output
    assert "--no-voice" in result.output
    assert "--list-voices" in result.output


def test_cli_list_voices():
    runner = CliRunner()
    result = runner.invoke(main, ["--list-voices"])
    assert result.exit_code == 0
    assert "Voices" in result.output or "Voice" in result.output
