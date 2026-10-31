"""Command dataclasses shared by all input handlers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class CommandType(Enum):
    # Playback
    PAUSE = auto()
    RESUME = auto()
    TOGGLE_PAUSE = auto()
    STOP = auto()
    QUIT = auto()
    # Navigation
    NEXT_SENTENCE = auto()
    PREV_SENTENCE = auto()
    NEXT_PAGE = auto()
    PREV_PAGE = auto()
    GOTO_PAGE = auto()
    REPEAT = auto()
    # Speed
    FASTER = auto()
    SLOWER = auto()
    SET_SPEED = auto()
    NORMAL_SPEED = auto()
    # Voice toggle
    TOGGLE_VOICE = auto()
    # Bookmarks
    BOOKMARK = auto()


@dataclass
class Command:
    """A command emitted by keyboard or voice handlers."""

    type: CommandType
    value: Optional[int | float | str] = None
    source: str = "keyboard"  # "keyboard" | "voice"

    def __repr__(self) -> str:
        v = f"({self.value})" if self.value is not None else ""
        return f"<Command {self.type.name}{v} via {self.source}>"
