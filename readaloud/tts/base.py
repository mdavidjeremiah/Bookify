"""Abstract TTS engine interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TTSEngine(ABC):
    """Abstract base for TTS engines."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak *text* synchronously (blocks until finished)."""

    @abstractmethod
    def stop(self) -> None:
        """Stop current utterance immediately."""

    @abstractmethod
    def set_rate(self, rate: float) -> None:
        """
        Set speech rate multiplier (1.0 = normal).
        Clamps to [0.5, 3.0].
        """

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set volume [0.0, 1.0]."""

    @abstractmethod
    def set_voice(self, voice_id: str) -> None:
        """Select a voice by its engine-specific ID."""

    @abstractmethod
    def list_voices(self) -> list[dict[str, str]]:
        """Return list of dicts with 'id', 'name', 'lang' keys."""

    @abstractmethod
    def cleanup(self) -> None:
        """Release all resources."""
