"""Legacy .doc / .ppt loader via LibreOffice conversion."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .base import DocumentLoader, Page

log = logging.getLogger(__name__)


class LegacyLoader(DocumentLoader):
    """Convert .doc/.ppt to .docx/.pptx via LibreOffice, then delegate."""

    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        ext = self.path.suffix.lower()
        modern = ".docx" if ext == ".doc" else ".pptx"

        if not soffice:
            raise RuntimeError(
                f"LibreOffice is required to open {ext!r} files.\n"
                f"Please install LibreOffice, or convert the file to {modern!r} first."
            )

        target_format = "docx" if ext == ".doc" else "pptx"

        with tempfile.TemporaryDirectory() as tmpdir:
            log.info("Converting %s via LibreOffice...", self.path.name)
            try:
                subprocess.run(
                    [
                        soffice,
                        "--headless",
                        "--convert-to",
                        target_format,
                        "--outdir",
                        tmpdir,
                        str(self.path),
                    ],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"LibreOffice conversion failed for {self.path.name}: {exc}"
                ) from exc

            converted = Path(tmpdir) / (self.path.stem + "." + target_format)
            if not converted.exists():
                raise RuntimeError(
                    f"LibreOffice conversion output not found for {self.path.name}"
                )

            from readaloud.loaders import get_loader

            loader = get_loader(converted)
            return loader.load()
