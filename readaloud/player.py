"""Reader/Player – owns playback state and drives TTS sentence by sentence."""

from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from readaloud.commands import Command, CommandType
from readaloud.loaders.base import Page
from readaloud.tts.base import TTSEngine

log = logging.getLogger(__name__)

SPEED_STEP = 0.1
SPEED_MIN = 0.5
SPEED_MAX = 3.0


@dataclass
class PlaybackState:
    page_index: int = 0
    sentence_index: int = 0
    speed: float = 1.0
    paused: bool = False
    stopped: bool = False
    last_command_label: str = ""
    voice_enabled: bool = True
    voice_state: str = "off"  # "off", "listening", "muted", "waiting"
    bookmarks: list[tuple[int, int]] = field(default_factory=list)  # list of (page, sentence)


class Player:
    """
    Drives TTS playback of a list of Pages.

    Keyboard and voice handlers push Command objects onto *cmd_queue*.
    The player loop polls the queue between sentences and immediately handles commands.
    """

    def __init__(
        self,
        pages: list[Page],
        engine: TTSEngine,
        cmd_queue: queue.Queue,
        initial_state: Optional[PlaybackState] = None,
        on_state_change: Optional[Callable[[PlaybackState], None]] = None,
        sleep_seconds: Optional[float] = None,
    ) -> None:
        self._pages = pages
        self._engine = engine
        self._cmd_queue = cmd_queue
        self._on_state_change = on_state_change
        self._sleep_seconds = sleep_seconds
        self._start_time: Optional[float] = None

        self.state = initial_state or PlaybackState()
        # Event set while TTS is actively speaking (used by voice listener to mute)
        self.speaking_event = threading.Event()

    def run(self) -> None:
        """Main blocking loop. Returns when stopped or all pages are done."""
        self._start_time = time.monotonic()
        self._set_speed(self.state.speed)
        self._notify()

        while not self.state.stopped:
            if self._sleep_timer_expired():
                log.info("Sleep timer expired – stopping.")
                self.state.stopped = True
                break

            self._drain_commands()

            if self.state.stopped:
                break

            if self.state.paused:
                time.sleep(0.08)
                continue

            sentence = self._current_sentence()
            if sentence is None:
                # Reached end of document
                log.info("Reached end of document.")
                break

            self.speaking_event.set()
            try:
                self._engine.speak(sentence)
            except Exception as exc:
                log.warning("TTS error while speaking: %s", exc)
            finally:
                self.speaking_event.clear()

            # Drain commands that arrived during speech
            self._drain_commands()

            # Advance to next sentence if not interrupted/paused/stopped
            if not self.state.paused and not self.state.stopped:
                self._advance()

        self._engine.cleanup()
        log.info("Playback loop finished.")

    def _current_sentence(self) -> Optional[str]:
        pi, si = self.state.page_index, self.state.sentence_index
        if pi >= len(self._pages):
            return None
        page = self._pages[pi]
        if si >= len(page.sentences):
            return None
        return page.sentences[si]

    def _advance(self) -> None:
        pi, si = self.state.page_index, self.state.sentence_index
        if pi >= len(self._pages):
            return
        page = self._pages[pi]
        si += 1
        if si >= len(page.sentences):
            pi += 1
            si = 0
            # Skip any empty pages if present
            while pi < len(self._pages) and not self._pages[pi].sentences:
                pi += 1
        self.state.page_index = pi
        self.state.sentence_index = si
        self._notify()

    def _drain_commands(self) -> None:
        while True:
            try:
                cmd: Command = self._cmd_queue.get_nowait()
                self._handle(cmd)
            except queue.Empty:
                break

    def _handle(self, cmd: Command) -> None:
        log.debug("Handling command: %s", cmd)
        source_tag = f" ({cmd.source})" if cmd.source else ""
        self.state.last_command_label = f"{cmd.type.name.replace('_', ' ').title()}{source_tag}"
        ct = cmd.type

        if ct == CommandType.PAUSE:
            self.state.paused = True
            self._engine.stop()
        elif ct == CommandType.RESUME:
            self.state.paused = False
        elif ct == CommandType.TOGGLE_PAUSE:
            if self.state.paused:
                self.state.paused = False
            else:
                self.state.paused = True
                self._engine.stop()
        elif ct in (CommandType.STOP, CommandType.QUIT):
            self.state.stopped = True
            self._engine.stop()
        elif ct == CommandType.NEXT_SENTENCE:
            self._engine.stop()
            self._advance()
        elif ct == CommandType.PREV_SENTENCE:
            self._engine.stop()
            self._go_back_sentence()
        elif ct == CommandType.NEXT_PAGE:
            self._engine.stop()
            self._go_next_page()
        elif ct == CommandType.PREV_PAGE:
            self._engine.stop()
            self._go_prev_page()
        elif ct == CommandType.GOTO_PAGE:
            if cmd.value is not None:
                self._engine.stop()
                self._goto_page(int(cmd.value) - 1)  # user gives 1-based page number
        elif ct == CommandType.REPEAT:
            self._engine.stop()
            # Speech loop will speak current (page_index, sentence_index) again
        elif ct == CommandType.FASTER:
            self._change_speed(SPEED_STEP)
        elif ct == CommandType.SLOWER:
            self._change_speed(-SPEED_STEP)
        elif ct == CommandType.NORMAL_SPEED:
            self._set_speed(1.0)
        elif ct == CommandType.SET_SPEED:
            if cmd.value is not None:
                self._set_speed(float(cmd.value))
        elif ct == CommandType.TOGGLE_VOICE:
            self.state.voice_enabled = not self.state.voice_enabled
        elif ct == CommandType.BOOKMARK:
            bm = (self.state.page_index, self.state.sentence_index)
            if bm not in self.state.bookmarks:
                self.state.bookmarks.append(bm)
                self.state.last_command_label = f"Bookmarked P{bm[0] + 1}:S{bm[1] + 1}"

        self._notify()

    def _change_speed(self, delta: float) -> None:
        new_speed = round(self.state.speed + delta, 1)
        self._set_speed(new_speed)

    def _set_speed(self, speed: float) -> None:
        self.state.speed = max(SPEED_MIN, min(SPEED_MAX, round(speed, 2)))
        self._engine.set_rate(self.state.speed)

    def _go_back_sentence(self) -> None:
        si = self.state.sentence_index - 1
        pi = self.state.page_index
        if si < 0:
            if pi > 0:
                pi -= 1
                while pi > 0 and not self._pages[pi].sentences:
                    pi -= 1
                si = max(0, len(self._pages[pi].sentences) - 1)
            else:
                si = 0
        self.state.page_index = pi
        self.state.sentence_index = max(0, si)

    def _go_next_page(self) -> None:
        pi = self.state.page_index + 1
        if pi < len(self._pages):
            self.state.page_index = pi
            self.state.sentence_index = 0

    def _go_prev_page(self) -> None:
        pi = self.state.page_index - 1
        if pi >= 0:
            self.state.page_index = pi
            self.state.sentence_index = 0

    def _goto_page(self, page_index: int) -> None:
        if 0 <= page_index < len(self._pages):
            self.state.page_index = page_index
            self.state.sentence_index = 0
        else:
            log.warning("Page %d out of range (1-%d)", page_index + 1, len(self._pages))

    def _sleep_timer_expired(self) -> bool:
        if self._sleep_seconds is None or self._start_time is None:
            return False
        return (time.monotonic() - self._start_time) >= self._sleep_seconds

    def _notify(self) -> None:
        if self._on_state_change:
            try:
                self._on_state_change(self.state)
            except Exception as exc:
                log.debug("State change notification error: %s", exc)
