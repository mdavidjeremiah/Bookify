"""Voice command handler – wraps VoskListener and emits Commands."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Optional

from readaloud.commands import Command, CommandType

log = logging.getLogger(__name__)

_VOICE_CMD_MAP: dict[str, tuple[CommandType, Optional[int | float]]] = {
    "pause": (CommandType.PAUSE, None),
    "resume": (CommandType.RESUME, None),
    "faster": (CommandType.FASTER, None),
    "slower": (CommandType.SLOWER, None),
    "normal_speed": (CommandType.NORMAL_SPEED, None),
    "next": (CommandType.NEXT_SENTENCE, None),
    "previous": (CommandType.PREV_SENTENCE, None),
    "repeat": (CommandType.REPEAT, None),
    "next_page": (CommandType.NEXT_PAGE, None),
    "previous_page": (CommandType.PREV_PAGE, None),
    "quit": (CommandType.QUIT, None),
    "bookmark": (CommandType.BOOKMARK, None),
}


class VoiceHandler:
    """Bridges VoskListener -> Command queue."""

    def __init__(
        self,
        cmd_queue: queue.Queue,
        model_path: Optional[str] = None,
        device: Optional[int] = None,
        wake_word: Optional[str] = "reader",
        speaking_event: Optional[threading.Event] = None,
        push_to_talk: bool = False,
    ) -> None:
        self._queue = cmd_queue
        self._model_path = model_path
        self._device = device
        self._wake_word = None if push_to_talk else wake_word
        self._speaking_event = speaking_event
        self._listener = None
        self._enabled = True

    def start(self) -> None:
        try:
            from readaloud.stt.vosk_listener import VoskListener
        except ImportError:
            log.warning("Vosk listener not available – voice control disabled.")
            return

        self._listener = VoskListener(
            callback=self._on_command,
            model_path=self._model_path,
            device=self._device,
            wake_word=self._wake_word,
            mute_event=self._speaking_event,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()

    def join(self, timeout: float = 2.0) -> None:
        if self._listener:
            self._listener.join(timeout=timeout)

    def _on_command(self, cmd_str: str, value: Optional[int]) -> None:
        log.info("Voice command recognized: %r (val=%r)", cmd_str, value)
        if not self._enabled:
            return

        if cmd_str == "goto_page" and value is not None:
            self._queue.put(Command(CommandType.GOTO_PAGE, value=value, source="voice"))
            return

        mapping = _VOICE_CMD_MAP.get(cmd_str)
        if mapping:
            cmd_type, cmd_val = mapping
            self._queue.put(Command(cmd_type, value=cmd_val, source="voice"))
        else:
            log.debug("Unrecognised voice command string: %r", cmd_str)
