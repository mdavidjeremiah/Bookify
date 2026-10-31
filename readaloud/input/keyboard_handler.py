"""Non-blocking keyboard listener."""

from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional

from readaloud.commands import Command, CommandType

log = logging.getLogger(__name__)


class KeyboardHandler:
    """
    Listens for key presses in a background thread and pushes Command objects
    into *cmd_queue*.

    Key map:
        Space       -> TOGGLE_PAUSE
        + / =       -> FASTER
        -           -> SLOWER
        Right arrow -> NEXT_SENTENCE
        Left arrow  -> PREV_SENTENCE
        n           -> NEXT_PAGE
        p           -> PREV_PAGE
        g           -> prompt goto page
        r           -> REPEAT
        v           -> TOGGLE_VOICE
        b           -> BOOKMARK
        q           -> QUIT
    """

    def __init__(
        self,
        cmd_queue: queue.Queue,
        goto_page_callback: Optional[Callable[[], Optional[int]]] = None,
    ) -> None:
        self._queue = cmd_queue
        self._goto_cb = goto_page_callback
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="keyboard-listener"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float = 2.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        try:
            from pynput import keyboard  # type: ignore
        except (ImportError, Exception) as exc:
            log.warning("pynput keyboard listener unavailable (%s).", exc)
            return

        def on_press(key):
            if self._stop_event.is_set():
                return False  # stop listener
            cmd = self._map_key(key)
            if cmd:
                self._queue.put(cmd)

        try:
            with keyboard.Listener(on_press=on_press, suppress=False) as listener:
                while not self._stop_event.is_set():
                    self._stop_event.wait(timeout=0.2)
                listener.stop()
        except Exception as exc:
            log.debug("Keyboard listener loop error: %s", exc)

    def _map_key(self, key) -> Optional[Command]:
        try:
            from pynput.keyboard import Key, KeyCode  # type: ignore
        except ImportError:
            return None

        char = getattr(key, "char", None)

        if key == Key.space:
            return Command(CommandType.TOGGLE_PAUSE, source="keyboard")
        if char in ("+", "="):
            return Command(CommandType.FASTER, source="keyboard")
        if char in ("-", "_"):
            return Command(CommandType.SLOWER, source="keyboard")
        if key == Key.right:
            return Command(CommandType.NEXT_SENTENCE, source="keyboard")
        if key == Key.left:
            return Command(CommandType.PREV_SENTENCE, source="keyboard")
        if char == "n":
            return Command(CommandType.NEXT_PAGE, source="keyboard")
        if char == "p":
            return Command(CommandType.PREV_PAGE, source="keyboard")
        if char == "r":
            return Command(CommandType.REPEAT, source="keyboard")
        if char == "v":
            return Command(CommandType.TOGGLE_VOICE, source="keyboard")
        if char == "b":
            return Command(CommandType.BOOKMARK, source="keyboard")
        if char == "q":
            return Command(CommandType.QUIT, source="keyboard")

        if char == "g":
            if self._goto_cb:
                page = self._goto_cb()
                if page is not None:
                    return Command(CommandType.GOTO_PAGE, value=page, source="keyboard")
            return None

        return None
