"""Tests for Vosk voice command dispatching and grammar."""

from readaloud.stt.vosk_listener import VoskListener, parse_page_number


def test_parse_page_number():
    assert parse_page_number("12") == 12
    assert parse_page_number("five") == 5
    assert parse_page_number("twenty") == 20
    assert parse_page_number("invalid") is None


def test_dispatch_with_wake_word():
    dispatched = []

    def callback(cmd, val):
        dispatched.append((cmd, val))

    listener = VoskListener(callback=callback, wake_word="reader")

    # Command without wake word should be ignored
    listener.dispatch_text("pause")
    assert len(dispatched) == 0

    # Command with wake word
    listener.dispatch_text("reader pause")
    assert dispatched == [("pause", None)]

    # "reader faster"
    listener.dispatch_text("reader faster")
    assert dispatched[-1] == ("faster", None)

    # "reader go to page 42"
    listener.dispatch_text("reader go to page 42")
    assert dispatched[-1] == ("goto_page", 42)

    # "reader go to page seven"
    listener.dispatch_text("reader go to page seven")
    assert dispatched[-1] == ("goto_page", 7)


def test_dispatch_without_wake_word_push_to_talk():
    dispatched = []

    def callback(cmd, val):
        dispatched.append((cmd, val))

    listener = VoskListener(callback=callback, wake_word=None)

    listener.dispatch_text("resume")
    assert dispatched == [("resume", None)]

    listener.dispatch_text("next page")
    assert dispatched[-1] == ("next_page", None)


def test_dispatch_unrecognized_silently_ignored():
    dispatched = []

    def callback(cmd, val):
        dispatched.append((cmd, val))

    listener = VoskListener(callback=callback, wake_word="reader")
    # Non-command random chatter should be ignored
    listener.dispatch_text("reader what is the weather today")
    assert len(dispatched) == 0
