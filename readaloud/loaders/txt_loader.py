"""Plain text / Markdown loader."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

_CHARS_PER_PAGE = 3000  # ~1 spoken minute per logical page


class TxtLoader(DocumentLoader):
    """Loader for .txt and .md files."""

    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        raw = self.path.read_text(encoding="utf-8", errors="replace")
        raw = clean_text(raw)

        if not raw.strip():
            raise ValueError("File appears to be empty.")

        chunks = _chunk(raw, _CHARS_PER_PAGE)
        pages: list[Page] = []
        for i, chunk in enumerate(chunks):
            sentences = split_sentences(chunk)
            if sentences:
                pages.append(Page(index=i, label=f"Page {i + 1}", sentences=sentences))

        if not pages:
            raise ValueError("No readable text found in file.")

        return pages


def _chunk(text: str, size: int) -> list[str]:
    """Split text into chunks of approximately *size* characters at sentence or word boundaries."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Backtrack to sentence or word boundary
        cut = -1
        for punct in (". ", "! ", "? ", "\n"):
            pos = text.rfind(punct, start, end)
            if pos != -1 and pos > cut:
                cut = pos + len(punct) - 1

        if cut == -1:
            cut = text.rfind(" ", start, end)
        if cut == -1:
            cut = end

        chunk = text[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        start = cut + 1
    return chunks
