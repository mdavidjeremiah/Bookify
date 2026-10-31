"""Terminal UI using rich."""

from __future__ import annotations

import threading
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from readaloud.player import PlaybackState

console = Console()

_SENTENCE_MAX = 80


class StatusDisplay:
    """
    Renders a live status panel using rich.Live.
    Call update() whenever the PlaybackState changes.
    """

    def __init__(self, filename: str, total_pages: int) -> None:
        self._filename = filename
        self._total = total_pages
        self._state: Optional[PlaybackState] = None
        self._current_sentence: str = ""
        self._lock = threading.Lock()
        self._live: Optional[Live] = None

    def start(self) -> None:
        if not console.is_terminal:
            return
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=4,
            transient=False,
        )
        try:
            self._live.start()
        except Exception:
            self._live = None

    def stop(self) -> None:
        if self._live:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None

    def update(self, state: PlaybackState, current_sentence: str = "") -> None:
        with self._lock:
            self._state = state
            self._current_sentence = current_sentence
        if self._live:
            try:
                self._live.update(self._render())
            except Exception:
                pass

    def _render(self) -> Panel:
        s = self._state
        filename = self._filename
        total = self._total

        if s is None:
            return Panel(Text("Loading…", style="dim"), title="readaloud")

        page_label = f"Page {s.page_index + 1} / {total}"

        sent = self._current_sentence or ""
        if len(sent) > _SENTENCE_MAX:
            sent = sent[: _SENTENCE_MAX - 3] + "…"

        status_icon = "⏸" if s.paused else "▶"
        status_style = "bold yellow" if s.paused else "bold green"
        speed_str = f"{s.speed:.1f}×"

        # Voice status
        if not s.voice_enabled:
            voice_str = "[dim]voice: off[/]"
        elif s.voice_state == "muted":
            voice_str = "[yellow]mic: muted (speaking)[/]"
        elif s.voice_state == "waiting":
            voice_str = "[cyan]voice: say \"reader …\"[/]"
        else:
            voice_str = "[green]voice: listening[/]"

        # Command status
        cmd_str = f" | Last: {s.last_command_label}" if s.last_command_label else ""

        table = Table.grid(expand=True, padding=(0, 1))
        table.add_column(ratio=3)
        table.add_column(ratio=2, justify="right")

        table.add_row(
            Text(filename, style="bold cyan"),
            Text(page_label, style="bold magenta"),
        )
        table.add_row(
            Text(f'"{sent}"' if sent else "...", style="italic white"),
            Text(""),
        )
        table.add_row(
            Text(
                f"{status_icon} {('Paused' if s.paused else 'Reading')} | Speed: {speed_str}{cmd_str}",
                style=status_style,
            ),
            Text.from_markup(voice_str),
        )

        hint = (
            "[dim]Controls:[/] [cyan]Space[/]:pause "
            "[cyan]+/-[/]:speed "
            "[cyan]←/→[/]:sentence "
            "[cyan]n/p[/]:page "
            "[cyan]g[/]:goto "
            "[cyan]r[/]:repeat "
            "[cyan]b[/]:bookmark "
            "[cyan]v[/]:voice "
            "[cyan]q[/]:quit"
        )
        table.add_row(Text.from_markup(hint), Text(""))

        return Panel(table, title="[bold blue]📖 readaloud[/]", border_style="blue")


# ---------------------------------------------------------------------------
# CLI helpers & prompts
# ---------------------------------------------------------------------------

def print_voices(voices: list[dict[str, str]]) -> None:
    table = Table(title="Installed TTS Voices", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Language", style="green")
    for i, v in enumerate(voices):
        table.add_row(str(i + 1), v.get("name", "Unknown"), v.get("id", ""), v.get("lang", "??"))
    console.print(table)


def print_error(msg: str) -> None:
    console.print(f"[bold red]Error:[/] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[cyan]{msg}[/]")


def print_warning(msg: str) -> None:
    console.print(f"[bold yellow]Warning:[/] {msg}")


def print_success(msg: str) -> None:
    console.print(f"[bold green]✔[/] {msg}")


def ask_resume(filename: str, page: int, sentence: int) -> bool:
    """Prompt user whether to resume from saved location."""
    console.print(
        f"\n[cyan]Found saved position in[/] [bold]{filename}[/]: "
        f"Page {page + 1}, Sentence {sentence + 1}."
    )
    try:
        answer = console.input("[cyan]Resume from here?[/] [dim](Y/n):[/] ").strip().lower()
        return answer in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def ask_goto_page(total_pages: int) -> Optional[int]:
    """Prompt user for a page number."""
    try:
        answer = console.input(f"[cyan]Go to page[/] [dim](1-{total_pages}):[/] ")
        page = int(answer.strip())
        if 1 <= page <= total_pages:
            return page
    except (ValueError, EOFError, KeyboardInterrupt):
        pass
    return None


def pick_file(directory: str = ".") -> Optional[str]:
    """Interactive file picker listing supported files in the current directory."""
    from pathlib import Path
    from readaloud.loaders import SUPPORTED_EXTENSIONS

    p = Path(directory)
    files = sorted(
        f for f in p.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not files:
        print_error(
            f"No supported files found in current directory ({directory}).\n"
            f"Supported extensions: {', '.join(sorted(SUPPORTED_EXTENSIONS))}\n"
            f"Usage: readaloud <path-to-file>"
        )
        return None

    table = Table(title="Select a Document to Read", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("File Name", style="bold")
    table.add_column("Type", style="cyan")
    table.add_column("Size", style="dim")

    for i, f in enumerate(files):
        sz = f.stat().st_size
        sz_str = f"{sz / 1024:.1f} KB" if sz < 1024 * 1024 else f"{sz / (1024*1024):.1f} MB"
        table.add_row(str(i + 1), f.name, f.suffix.lower(), sz_str)

    console.print(table)

    try:
        choice = console.input("[cyan]Enter file number to read (or 'q' to cancel):[/] ").strip()
        if choice.lower() in ("q", "quit", "exit"):
            return None
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            return str(files[idx])
    except (ValueError, EOFError, KeyboardInterrupt):
        pass

    print_error("Invalid selection.")
    return None
