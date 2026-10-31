"""DOCX loader using python-docx."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

_CHARS_PER_PAGE = 3000


class DocxLoader(DocumentLoader):
    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            from docx import Document  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "python-docx is required to read .docx files.\n"
                "Install it with: pip install python-docx"
            ) from exc

        doc = Document(str(self.path))

        all_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        all_text = clean_text(all_text)

        if not all_text.strip():
            raise ValueError("No readable text found in this DOCX file.")

        from .txt_loader import _chunk

        chunks = _chunk(all_text, _CHARS_PER_PAGE)
        pages: list[Page] = []
        for i, chunk in enumerate(chunks):
            sentences = split_sentences(chunk)
            if sentences:
                pages.append(Page(index=i, label=f"Page {i + 1}", sentences=sentences))

        if not pages:
            raise ValueError("No readable text found in this DOCX file.")

        return pages
