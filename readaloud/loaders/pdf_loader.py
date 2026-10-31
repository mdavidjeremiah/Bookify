"""PDF loader – prefers PyMuPDF, falls back to pypdf."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

log = logging.getLogger(__name__)


class PdfLoader(DocumentLoader):
    """Extract text from PDF files."""

    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            return self._load_fitz()
        except ImportError:
            log.debug("PyMuPDF not available, falling back to pypdf")

        try:
            return self._load_pypdf()
        except ImportError as exc:
            raise ImportError(
                "Either PyMuPDF or pypdf is required to read .pdf files.\n"
                "Install with: pip install pypdf"
            ) from exc

    def _load_fitz(self) -> list[Page]:
        import fitz  # PyMuPDF

        doc = fitz.open(str(self.path))
        pages: list[Page] = []
        total_text = 0

        for i, fitz_page in enumerate(doc):
            raw = fitz_page.get_text("text")  # type: ignore[attr-defined]
            text = clean_text(raw)
            if text:
                total_text += len(text)
                sentences = split_sentences(text)
                if sentences:
                    pages.append(
                        Page(index=i, label=f"Page {i + 1}", sentences=sentences)
                    )

        doc.close()
        self._check_empty(total_text, pages)
        return pages

    def _load_pypdf(self) -> list[Page]:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(self.path))
        pages: list[Page] = []
        total_text = 0

        for i, pdf_page in enumerate(reader.pages):
            raw = pdf_page.extract_text() or ""
            text = clean_text(raw)
            if text:
                total_text += len(text)
                sentences = split_sentences(text)
                if sentences:
                    pages.append(
                        Page(index=i, label=f"Page {i + 1}", sentences=sentences)
                    )

        self._check_empty(total_text, pages)
        return pages

    @staticmethod
    def _check_empty(total_text: int, pages: list[Page]) -> None:
        if total_text == 0 or not pages:
            raise ValueError(
                "No extractable text found in this PDF.\n"
                "This is likely a scanned / image-only PDF.\n"
                "OCR support is planned for v2."
            )
