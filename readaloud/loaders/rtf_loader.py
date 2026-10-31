"""RTF loader using striprtf."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

_CHARS_PER_PAGE = 3000


class RtfLoader(DocumentLoader):
    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            from striprtf.striprtf import rtf_to_text  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "striprtf is required to read .rtf files.\n"
                "Install with: pip install striprtf"
            ) from exc

        raw_rtf = self.path.read_text(encoding="utf-8", errors="replace")
        text = rtf_to_text(raw_rtf)
        text = clean_text(text)

        if not text.strip():
            raise ValueError("No readable text found in this RTF file.")

        from .txt_loader import _chunk

        chunks = _chunk(text, _CHARS_PER_PAGE)
        pages: list[Page] = []
        for i, chunk in enumerate(chunks):
            sentences = split_sentences(chunk)
            if sentences:
                pages.append(Page(index=i, label=f"Page {i + 1}", sentences=sentences))

        if not pages:
            raise ValueError("No readable text found in this RTF file.")

        return pages
