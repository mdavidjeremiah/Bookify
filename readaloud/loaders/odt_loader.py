"""ODT (OpenDocument Text) loader using odfpy."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

_CHARS_PER_PAGE = 3000


class OdtLoader(DocumentLoader):
    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            from odf.opendocument import load as odf_load  # type: ignore
            from odf.text import P, H  # type: ignore
            from odf import teletype  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "odfpy is required to read .odt files.\n"
                "Install it with: pip install odfpy"
            ) from exc

        doc = odf_load(str(self.path))
        paragraphs = []
        for element in doc.getElementsByType(H) + doc.getElementsByType(P):
            t = teletype.extractText(element).strip()
            if t:
                paragraphs.append(t)

        all_text = clean_text("\n".join(paragraphs))

        if not all_text.strip():
            raise ValueError("No readable text found in this ODT file.")

        from .txt_loader import _chunk

        chunks = _chunk(all_text, _CHARS_PER_PAGE)
        pages: list[Page] = []
        for i, chunk in enumerate(chunks):
            sentences = split_sentences(chunk)
            if sentences:
                pages.append(Page(index=i, label=f"Page {i + 1}", sentences=sentences))

        if not pages:
            raise ValueError("No readable text found in this ODT file.")

        return pages
