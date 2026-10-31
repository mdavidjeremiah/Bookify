"""Tests for command dataclasses and enums."""

from readaloud.commands import Command, CommandType


def test_command_creation():
    cmd = Command(type=CommandType.PAUSE, source="keyboard")
    assert cmd.type == CommandType.PAUSE
    assert cmd.value is None
    assert cmd.source == "keyboard"
    assert "PAUSE" in repr(cmd)


def test_command_with_value():
    cmd = Command(type=CommandType.GOTO_PAGE, value=42, source="voice")
    assert cmd.type == CommandType.GOTO_PAGE
    assert cmd.value == 42
    assert cmd.source == "voice"
    assert "42" in repr(cmd)
