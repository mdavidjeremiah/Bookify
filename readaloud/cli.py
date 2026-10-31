"""CLI entry point for readaloud."""

from __future__ import annotations

import logging
import queue
import re
import sys
from pathlib import Path
from typing import Optional

import click

from readaloud import __version__
from readaloud.persistence import ConfigStore, PositionStore, file_hash
from readaloud.player import PlaybackState, Player
from readaloud.tts.pyttsx3_engine import Pyttsx3Engine
from readaloud import ui

log = logging.getLogger(__name__)


def parse_duration(value: str) -> float:
    """Parse duration strings such as '30m', '1h', '45s', or raw numbers into seconds."""
    value = value.strip().lower()
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(s|m|h)?", value)
    if not m:
        raise click.BadParameter(f"Invalid duration: {value!r}. Use format like 30m, 1h, 90s.")
    amount = float(m.group(1))
    unit = m.group(2) or "s"
    multipliers = {"s": 1.0, "m": 60.0, "h": 3600.0}
    return amount * multipliers[unit]


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("file", required=False, type=click.Path(exists=False))
@click.option("--speed", type=float, default=None, help="Initial speed multiplier (e.g. 1.2; default 1.0)")
@click.option("--page", "start_page", type=int, default=None, help="Start at page/slide (1-based)")
@click.option("--voice", "voice_name", type=str, default=None, help="TTS voice ID or name")
@click.option("--list-voices", is_flag=True, help="List installed voices and exit")
@click.option("--no-voice", is_flag=True, help="Disable voice commands")
@click.option("--push-to-talk", is_flag=True, help="Use push-to-talk instead of wake word")
@click.option("--mic", "mic_index", type=int, default=None, help="Microphone device index")
@click.option("--resume", "force_resume", is_flag=True, help="Resume from saved position without prompting")
@click.option("--sleep", "sleep_duration", type=str, default=None, help="Stop automatically after duration, e.g. 30m")
@click.option("--setup", is_flag=True, help="Download/verify offline models")
@click.option("--version", is_flag=True, help="Show version and exit")
@click.option("--debug", is_flag=True, hidden=True)
def main(
    file: Optional[str],
    speed: Optional[float],
    start_page: Optional[int],
    voice_name: Optional[str],
    list_voices: bool,
    no_voice: bool,
    push_to_talk: bool,
    mic_index: Optional[int],
    force_resume: bool,
    sleep_duration: Optional[str],
    setup: bool,
    version: bool,
    debug: bool,
) -> None:
    """Offline voice-controlled document reader CLI."""
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if version:
        click.echo(f"readaloud {__version__}")
        return

    if setup:
        from readaloud.setup_models import run_setup
        run_setup()
        return

    # ------------------------------------------------------------------
    # Initialize TTS engine
    # ------------------------------------------------------------------
    try:
        engine = Pyttsx3Engine()
    except Exception as exc:
        ui.print_error(f"Could not initialize TTS engine: {exc}")
        sys.exit(1)

    if list_voices:
        ui.print_voices(engine.list_voices())
        engine.cleanup()
        return

    # ------------------------------------------------------------------
    # Load config and user preferences
    # ------------------------------------------------------------------
    cfg = ConfigStore()
    pos_store = PositionStore()

    effective_speed = speed if speed is not None else float(cfg.get("speed", 1.0))
    effective_voice = voice_name or cfg.get("voice")
    voice_enabled = (not no_voice) and bool(cfg.get("voice_enabled", True))
    effective_mic = mic_index if mic_index is not None else cfg.get("mic")

    engine.set_rate(effective_speed)
    if effective_voice:
        try:
            engine.set_voice(effective_voice)
        except Exception:
            ui.print_warning(f"Voice '{effective_voice}' not found, using default voice.")

    # ------------------------------------------------------------------
    # Resolve file path (or show file picker)
    # ------------------------------------------------------------------
    if not file:
        file = ui.pick_file(".")
        if not file:
            sys.exit(0)

    file_path = Path(file).resolve()
    if not file_path.exists():
        ui.print_error(f"File not found: {file}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Load document
    # ------------------------------------------------------------------
    ui.print_info(f"Loading '{file_path.name}'…")
    try:
        from readaloud.loaders import get_loader

        loader = get_loader(file_path)
        pages = loader.load()
    except (ValueError, RuntimeError) as exc:
        ui.print_error(str(exc))
        sys.exit(1)
    except ImportError as exc:
        ui.print_error(str(exc))
        sys.exit(1)
    except Exception as exc:
        ui.print_error(f"Failed to load '{file_path.name}': {exc}")
        if debug:
            raise
        sys.exit(1)

    if not pages:
        ui.print_error("Document contains no readable pages.")
        sys.exit(1)

    total_sentences = sum(len(p.sentences) for p in pages)
    ui.print_info(f"Loaded {len(pages)} page(s) ({total_sentences} sentences).")

    # ------------------------------------------------------------------
    # Determine start position (Resume check)
    # ------------------------------------------------------------------
    fhash = file_hash(file_path)
    saved = pos_store.get(fhash)
    initial_state = PlaybackState(speed=effective_speed)
    initial_state.voice_enabled = voice_enabled

    if saved and not force_resume and start_page is None:
        if ui.ask_resume(file_path.name, saved.get("page", 0), saved.get("sentence", 0)):
            initial_state.page_index = saved.get("page", 0)
            initial_state.sentence_index = saved.get("sentence", 0)
    elif saved and force_resume:
        initial_state.page_index = saved.get("page", 0)
        initial_state.sentence_index = saved.get("sentence", 0)

    if start_page is not None:
        initial_state.page_index = max(0, min(start_page - 1, len(pages) - 1))
        initial_state.sentence_index = 0

    # ------------------------------------------------------------------
    # Sleep timer
    # ------------------------------------------------------------------
    sleep_seconds: Optional[float] = None
    if sleep_duration:
        try:
            sleep_seconds = parse_duration(sleep_duration)
            ui.print_info(f"Sleep timer set for {sleep_duration} ({int(sleep_seconds)} seconds).")
        except click.BadParameter as exc:
            ui.print_error(str(exc))
            sys.exit(1)

    # ------------------------------------------------------------------
    # Command queue and Status Display
    # ------------------------------------------------------------------
    cmd_queue: queue.Queue = queue.Queue()
    display = ui.StatusDisplay(file_path.name, len(pages))

    def on_state_change(state: PlaybackState) -> None:
        pi = state.page_index
        si = state.sentence_index
        sent = ""
        if pi < len(pages) and si < len(pages[pi].sentences):
            sent = pages[pi].sentences[si]
        display.update(state, sent)

    # ------------------------------------------------------------------
    # Player initialization
    # ------------------------------------------------------------------
    player = Player(
        pages=pages,
        engine=engine,
        cmd_queue=cmd_queue,
        initial_state=initial_state,
        on_state_change=on_state_change,
        sleep_seconds=sleep_seconds,
    )

    # ------------------------------------------------------------------
    # Keyboard listener
    # ------------------------------------------------------------------
    from readaloud.input.keyboard_handler import KeyboardHandler

    def goto_page_dialog() -> Optional[int]:
        display.stop()
        page_num = ui.ask_goto_page(len(pages))
        display.start()
        return page_num

    kb_handler = KeyboardHandler(cmd_queue, goto_page_callback=goto_page_dialog)
    try:
        kb_handler.start()
    except Exception as exc:
        log.warning("Keyboard listener start failed: %s", exc)

    # ------------------------------------------------------------------
    # Voice listener
    # ------------------------------------------------------------------
    voice_handler = None
    if voice_enabled:
        from readaloud.input.voice_handler import VoiceHandler

        voice_handler = VoiceHandler(
            cmd_queue=cmd_queue,
            device=effective_mic,
            wake_word=None if push_to_talk else "reader",
            speaking_event=player.speaking_event,
            push_to_talk=push_to_talk,
        )
        try:
            voice_handler.start()
            initial_state.voice_state = "waiting" if not push_to_talk else "listening"
        except Exception as exc:
            log.warning("Voice handler start failed: %s", exc)
            initial_state.voice_state = "off"
            voice_handler = None
    else:
        initial_state.voice_state = "off"

    # ------------------------------------------------------------------
    # Run playback
    # ------------------------------------------------------------------
    display.start()
    try:
        player.run()
    except KeyboardInterrupt:
        pass
    finally:
        # Save position to persistence store
        pos_store.save(
            fhash,
            player.state.page_index,
            player.state.sentence_index,
            file_path.name,
        )
        # Update user default speed
        cfg.set("speed", player.state.speed)

        # Cleanup handlers
        kb_handler.stop()
        if voice_handler:
            voice_handler.stop()

        display.stop()

        ui.print_info(
            f"Saved position: Page {player.state.page_index + 1}, "
            f"Sentence {player.state.sentence_index + 1}."
        )


if __name__ == "__main__":
    main()
