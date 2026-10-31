"""pyttsx3 TTS engine implementation."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from .base import TTSEngine

log = logging.getLogger(__name__)

_BASE_RATE = 175  # pyttsx3 default words-per-minute


class Pyttsx3Engine(TTSEngine):
    """
    TTS engine backed by pyttsx3.

    Synchronous and thread-safe via internal lock.
    """

    def __init__(self) -> None:
        try:
            import pyttsx3  # type: ignore

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", _BASE_RATE)
        except Exception as exc:
            log.warning("pyttsx3 could not be initialized (%s). Using dummy TTS engine.", exc)
            self._engine = None

        self._lock = threading.Lock()
        self._rate_multiplier: float = 1.0
        self._is_stopped = False

    def speak(self, text: str) -> None:
        """Speak *text* synchronously. Blocks until speech is complete or stopped."""
        with self._lock:
            self._is_stopped = False
            if self._engine is not None:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as exc:
                    log.debug("pyttsx3 speak error: %s", exc)

    def stop(self) -> None:
        """Interrupt current speech."""
        with self._lock:
            self._is_stopped = True
            if self._engine is not None:
                try:
                    self._engine.stop()
                except Exception as exc:
                    log.debug("pyttsx3 stop error: %s", exc)

    def set_rate(self, rate: float) -> None:
        rate = max(0.5, min(3.0, rate))
        self._rate_multiplier = rate
        wpm = int(_BASE_RATE * rate)
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.setProperty("rate", wpm)
                except Exception as exc:
                    log.debug("pyttsx3 set rate error: %s", exc)
        log.debug("TTS rate set to %.1fx (%d wpm)", rate, wpm)

    def set_volume(self, volume: float) -> None:
        volume = max(0.0, min(1.0, volume))
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.setProperty("volume", volume)
                except Exception as exc:
                    log.debug("pyttsx3 set volume error: %s", exc)

    def set_voice(self, voice_id: str) -> None:
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.setProperty("voice", voice_id)
                except Exception as exc:
                    log.debug("pyttsx3 set voice error: %s", exc)

    def list_voices(self) -> list[dict[str, str]]:
        if self._engine is None:
            return [{"id": "dummy", "name": "Dummy Voice", "lang": "en"}]
        try:
            voices = self._engine.getProperty("voices") or []
            return [
                {
                    "id": getattr(v, "id", str(v)),
                    "name": getattr(v, "name", str(v)),
                    "lang": (getattr(v, "languages", ["??"])[0] if getattr(v, "languages", None) else "??"),
                }
                for v in voices
            ]
        except Exception as exc:
            log.debug("pyttsx3 list voices error: %s", exc)
            return []

    def cleanup(self) -> None:
        try:
            self.stop()
        except Exception:
            pass
