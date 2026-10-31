"""Speech-to-text (voice command) package."""
from .vosk_listener import VoskListener, COMMAND_PHRASES, WAKE_WORD

__all__ = ["VoskListener", "COMMAND_PHRASES", "WAKE_WORD"]
