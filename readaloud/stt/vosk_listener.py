"""Offline voice command recognizer using Vosk."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Callable, Optional

log = logging.getLogger(__name__)

# Map of normalised phrase -> canonical command identifier
COMMAND_PHRASES: dict[str, str] = {
    "pause": "pause",
    "stop reading": "pause",
    "resume": "resume",
    "continue": "resume",
    "faster": "faster",
    "speed up": "faster",
    "slower": "slower",
    "slow down": "slower",
    "normal speed": "normal_speed",
    "next": "next",
    "skip": "next",
    "back": "previous",
    "previous": "previous",
    "repeat": "repeat",
    "next page": "next_page",
    "previous page": "previous_page",
    "quit": "quit",
    "exit": "quit",
}

# Number words to digit mapping for natural speech (e.g. "go to page five")
_WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_GRAMMAR_WORDS = sorted(
    {w for phrase in COMMAND_PHRASES for w in phrase.split()}
    | {"reader", "go", "to", "page"}
    | set(_WORD_TO_NUM.keys())
    | {str(i) for i in range(0, 1000)}
)

WAKE_WORD = "reader"
_GOTO_RE = re.compile(r"(?:go\s+to\s+)?(?:page\s+)?(\d+|\w+)", re.IGNORECASE)


def parse_page_number(token: str) -> Optional[int]:
    """Parse number from digit or word."""
    token = token.strip().lower()
    if token.isdigit():
        return int(token)
    if token in _WORD_TO_NUM:
        return _WORD_TO_NUM[token]
    return None


class VoskListener:
    """
    Continuously listens on the microphone and calls *callback* with
    recognized command strings and optional parameters.
    """

    def __init__(
        self,
        callback: Callable[[str, Optional[int]], None],
        model_path: Optional[str] = None,
        device: Optional[int] = None,
        wake_word: Optional[str] = WAKE_WORD,
        mute_event: Optional[threading.Event] = None,
    ) -> None:
        self._callback = callback
        self._model_path = model_path
        self._device = device
        self._wake_word = wake_word.lower() if wake_word else None
        self._mute_event = mute_event
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the listener thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="vosk-listener"
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the listener thread to stop."""
        self._stop_event.set()

    def join(self, timeout: float = 2.0) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        try:
            import vosk  # type: ignore
            import sounddevice as sd  # type: ignore
        except ImportError:
            log.warning(
                "vosk or sounddevice not installed – voice control disabled.\n"
                "Install with: pip install readaloud[voice]"
            )
            return

        model_path = self._model_path or self._find_model()
        if model_path is None or not Path(model_path).exists():
            log.warning(
                "Vosk model not found. Run `readaloud --setup` to download it."
            )
            return

        # Suppress vosk internal log spam
        try:
            vosk.SetLogLevel(-1)
        except Exception:
            pass

        try:
            model = vosk.Model(str(model_path))
            grammar_json = json.dumps(_GRAMMAR_WORDS)
            rec = vosk.KaldiRecognizer(model, 16000, grammar_json)
        except Exception as exc:
            log.warning("Failed to initialize Vosk model: %s", exc)
            return

        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=4000,
                dtype="int16",
                channels=1,
                device=self._device,
            ) as stream:
                log.info("Voice control active. Wake word: %r", self._wake_word)
                while not self._stop_event.is_set():
                    # Check mute event for self-hearing mitigation
                    if self._mute_event and self._mute_event.is_set():
                        # Read and discard audio while speaking to prevent buffer buildup
                        stream.read(2000)
                        continue

                    data, overflowed = stream.read(2000)
                    if overflowed:
                        log.debug("Microphone buffer overflowed")
                    if rec.AcceptWaveform(bytes(data)):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip().lower()
                        if text:
                            self.dispatch_text(text)
        except Exception as exc:
            log.warning("Microphone stream error: %s", exc)

    def dispatch_text(self, text: str) -> None:
        """Process recognised raw text and trigger callback if matches grammar."""
        text = text.strip().lower()
        log.debug("Heard voice input: %r", text)

        if self._wake_word:
            if not text.startswith(self._wake_word):
                return
            # Strip the wake word
            text = text[len(self._wake_word):].strip()

        if not text:
            return

        # Check for "go to page [N]" or "page [N]"
        goto_m = re.search(r"(?:go\s+to\s+)?page\s+(\w+)", text)
        if goto_m:
            page_val = parse_page_number(goto_m.group(1))
            if page_val is not None:
                self._callback("goto_page", page_val)
                return

        # Match phrases (checking longest match first)
        for phrase in sorted(COMMAND_PHRASES.keys(), key=len, reverse=True):
            if phrase in text:
                self._callback(COMMAND_PHRASES[phrase], None)
                return

    @staticmethod
    def _find_model() -> Optional[str]:
        """Search default locations for a Vosk model directory."""
        from platformdirs import user_data_dir

        candidates = [
            Path(user_data_dir("readaloud", "readaloud")) / "vosk-model",
            Path.home() / ".local" / "share" / "vosk-model-small-en-us",
            Path.home() / ".cache" / "vosk" / "vosk-model-small-en-us",
            Path("/usr/share/vosk/model"),
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        return None
