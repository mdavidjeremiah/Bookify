"""Tests for Player state machine and playback commands."""

import queue
import time
from unittest.mock import MagicMock

from readaloud.commands import Command, CommandType
from readaloud.loaders.base import Page
from readaloud.player import PlaybackState, Player, SPEED_MIN, SPEED_MAX


class DummyTTS:
    def __init__(self):
        self.spoken = []
        self.rate = 1.0
        self.stopped = False

    def speak(self, text: str):
        self.spoken.append(text)

    def stop(self):
        self.stopped = True

    def set_rate(self, rate: float):
        self.rate = rate

    def set_volume(self, volume: float):
        pass

    def set_voice(self, voice_id: str):
        pass

    def list_voices(self):
        return []

    def cleanup(self):
        pass


def test_player_basic_run():
    pages = [
        Page(index=0, label="Page 1", sentences=["Sentence 1.", "Sentence 2."]),
        Page(index=1, label="Page 2", sentences=["Sentence 3."]),
    ]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q)

    player.run()

    assert tts.spoken == ["Sentence 1.", "Sentence 2.", "Sentence 3."]
    assert player.state.page_index == 2  # completed all pages


def test_player_speed_commands():
    pages = [Page(index=0, label="P1", sentences=["S1."])]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q)

    # Faster
    cmd_q.put(Command(CommandType.FASTER))
    player._drain_commands()
    assert player.state.speed == 1.1

    # Slower
    cmd_q.put(Command(CommandType.SLOWER))
    player._drain_commands()
    assert player.state.speed == 1.0

    # Normal speed
    cmd_q.put(Command(CommandType.SET_SPEED, value=2.5))
    player._drain_commands()
    assert player.state.speed == 2.5

    cmd_q.put(Command(CommandType.NORMAL_SPEED))
    player._drain_commands()
    assert player.state.speed == 1.0

    # Clamping
    cmd_q.put(Command(CommandType.SET_SPEED, value=10.0))
    player._drain_commands()
    assert player.state.speed == SPEED_MAX

    cmd_q.put(Command(CommandType.SET_SPEED, value=0.1))
    player._drain_commands()
    assert player.state.speed == SPEED_MIN


def test_player_navigation_commands():
    pages = [
        Page(index=0, label="P1", sentences=["P1S1.", "P1S2."]),
        Page(index=1, label="P2", sentences=["P2S1.", "P2S2."]),
        Page(index=2, label="P3", sentences=["P3S1."]),
    ]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q)

    # Advance sentence
    cmd_q.put(Command(CommandType.NEXT_SENTENCE))
    player._drain_commands()
    assert player.state.page_index == 0
    assert player.state.sentence_index == 1

    # Previous sentence
    cmd_q.put(Command(CommandType.PREV_SENTENCE))
    player._drain_commands()
    assert player.state.sentence_index == 0

    # Next page
    cmd_q.put(Command(CommandType.NEXT_PAGE))
    player._drain_commands()
    assert player.state.page_index == 1
    assert player.state.sentence_index == 0

    # Previous page
    cmd_q.put(Command(CommandType.PREV_PAGE))
    player._drain_commands()
    assert player.state.page_index == 0

    # Goto page (1-based: page 3 -> index 2)
    cmd_q.put(Command(CommandType.GOTO_PAGE, value=3))
    player._drain_commands()
    assert player.state.page_index == 2
    assert player.state.sentence_index == 0


def test_player_bookmarks():
    pages = [Page(index=0, label="P1", sentences=["S1.", "S2."])]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q)

    player.state.page_index = 0
    player.state.sentence_index = 1
    cmd_q.put(Command(CommandType.BOOKMARK))
    player._drain_commands()

    assert (0, 1) in player.state.bookmarks


def test_player_pause_toggle_stop():
    pages = [Page(index=0, label="P1", sentences=["S1."])]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q)

    cmd_q.put(Command(CommandType.TOGGLE_PAUSE))
    player._drain_commands()
    assert player.state.paused is True

    cmd_q.put(Command(CommandType.TOGGLE_PAUSE))
    player._drain_commands()
    assert player.state.paused is False

    cmd_q.put(Command(CommandType.STOP))
    player._drain_commands()
    assert player.state.stopped is True


def test_player_sleep_timer():
    pages = [Page(index=0, label="P1", sentences=["S1."])]
    tts = DummyTTS()
    cmd_q = queue.Queue()
    player = Player(pages=pages, engine=tts, cmd_queue=cmd_q, sleep_seconds=0.01)

    player._start_time = time.monotonic() - 0.05
    assert player._sleep_timer_expired() is True
