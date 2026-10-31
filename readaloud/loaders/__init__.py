"""Document loaders – format-specific extractors behind a common interface."""

from __future__ import annotations

import importlib
import logging
import zipfile
from pathlib import Path
from typing import Optional

from .base import DocumentLoader, Page

log = logging.getLogger(__name__)

_EXTENSION_MAP: dict[str, str] = {
    ".txt": "readaloud.loaders.txt_loader.TxtLoader",
    ".md": "readaloud.loaders.txt_loader.TxtLoader",
    ".pdf": "readaloud.loaders.pdf_loader.PdfLoader",
    ".docx": "readaloud.loaders.docx_loader.DocxLoader",
    ".odt": "readaloud.loaders.odt_loader.OdtLoader",
    ".pptx": "readaloud.loaders.pptx_loader.PptxLoader",
    ".epub": "readaloud.loaders.epub_loader.EpubLoader",
    ".rtf": "readaloud.loaders.rtf_loader.RtfLoader",
    ".doc": "readaloud.loaders.legacy_loader.LegacyLoader",
    ".ppt": "readaloud.loaders.legacy_loader.LegacyLoader",
}

SUPPORTED_EXTENSIONS = set(_EXTENSION_MAP.keys())


def _import_loader(dotted: str) -> type[DocumentLoader]:
    module_path, cls_name = dotted.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


def detect_format_by_signature(path: Path) -> Optional[str]:
    """Inspect magic numbers/file signature if extension is ambiguous or missing."""
    try:
        with open(path, "rb") as f:
            header = f.read(2048)
    except Exception:
        return None

    if header.startswith(b"%PDF"):
        return ".pdf"
    if header.startswith(b"{\\rtf"):
        return ".rtf"

    # ZIP-based formats (.docx, .pptx, .odt, .epub)
    if header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
        try:
            with zipfile.ZipFile(path, "r") as z:
                names = z.namelist()
                if "mimetype" in names:
                    mimetype_content = z.read("mimetype").decode("ascii", errors="ignore").strip()
                    if "epub" in mimetype_content:
                        return ".epub"
                    if "opendocument.text" in mimetype_content:
                        return ".odt"
                if any(n.startswith("word/") for n in names):
                    return ".docx"
                if any(n.startswith("ppt/") for n in names):
                    return ".pptx"
        except Exception:
            pass

    # OLE Compound Document (.doc, .ppt)
    if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        # Default legacy fallback
        return ".doc"

    # Check if text
    try:
        header.decode("utf-8")
        return ".txt"
    except UnicodeDecodeError:
        pass

    return None


def get_loader(path: str | Path) -> DocumentLoader:
    """Return the appropriate loader for *path*."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext not in _EXTENSION_MAP:
        # Fallback to signature detection
        detected = detect_format_by_signature(p)
        if detected and detected in _EXTENSION_MAP:
            ext = detected

    if ext not in _EXTENSION_MAP:
        raise ValueError(
            f"Unsupported file format: '{p.suffix}'.\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    loader_cls = _import_loader(_EXTENSION_MAP[ext])
    return loader_cls(p)


__all__ = ["DocumentLoader", "Page", "get_loader", "SUPPORTED_EXTENSIONS", "detect_format_by_signature"]
