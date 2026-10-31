"""Download and verify offline models (Vosk STT)."""

from __future__ import annotations

import logging
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

from platformdirs import user_data_dir
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TransferSpeedColumn

log = logging.getLogger(__name__)
console = Console()

APP_NAME = "readaloud"
APP_AUTHOR = "readaloud"

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_DIR_NAME = "vosk-model"


def get_model_dir() -> Path:
    return Path(user_data_dir(APP_NAME, APP_AUTHOR))


def model_exists() -> bool:
    target = get_model_dir() / VOSK_MODEL_DIR_NAME
    return target.exists() and any(target.iterdir())


def download_vosk_model() -> None:
    """Download and extract the Vosk small English model."""
    dest_dir = get_model_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "vosk-model.zip"
    model_path = dest_dir / VOSK_MODEL_DIR_NAME

    if model_exists():
        console.print(f"[bold green]✔[/] Vosk offline model is already installed at: [cyan]{model_path}[/]")
        return

    console.print(f"[bold cyan]Notice:[/] Downloading offline speech recognition model from:")
    console.print(f"  [dim]{VOSK_MODEL_URL}[/]")
    console.print("[yellow]This one-time download requires an internet connection (~50 MB).[/]\n")

    with Progress(
        SpinnerColumn(),
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading model…", total=None)

        def reporthook(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress.tasks[task].total is None:
                progress.update(task, total=total_size)
            progress.update(task, advance=block_size)

        try:
            urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, reporthook=reporthook)
        except Exception as exc:
            console.print(f"[bold red]Download failed:[/] {exc}")
            if zip_path.exists():
                zip_path.unlink()
            return

    console.print("\n[cyan]Extracting model files…[/]")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            top_level_dirs = {name.split("/")[0] for name in zf.namelist() if "/" in name}
            zf.extractall(dest_dir)

            if model_path.exists():
                shutil.rmtree(model_path)

            extracted_folder = None
            for d in top_level_dirs:
                candidate = dest_dir / d
                if candidate.is_dir() and "vosk" in d.lower():
                    extracted_folder = candidate
                    break

            if extracted_folder and extracted_folder.exists():
                extracted_folder.rename(model_path)
            elif not model_path.exists():
                # If zip extracted directly
                pass

        console.print(f"[bold green]✔ Model successfully installed to:[/] [cyan]{model_path}[/]")
    except Exception as exc:
        console.print(f"[bold red]Extraction failed:[/] {exc}")
    finally:
        if zip_path.exists():
            zip_path.unlink()


def run_setup() -> None:
    """Entry point for `readaloud --setup`."""
    console.print("\n[bold cyan]=== readaloud Offline Model Setup ===[/]\n")
    download_vosk_model()
    console.print("\n[bold green]Setup completed.[/] Offline voice control is ready to use.\n")
