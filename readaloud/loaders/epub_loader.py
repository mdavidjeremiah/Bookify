"""EPUB loader using ebooklib + BeautifulSoup."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences

log = logging.getLogger(__name__)


class EpubLoader(DocumentLoader):
    """Each spine item / chapter becomes one page."""

    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            import ebooklib  # type: ignore
            from ebooklib import epub  # type: ignore
            from bs4 import BeautifulSoup  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "ebooklib and beautifulsoup4 are required for .epub files.\n"
                "Install with: pip install ebooklib beautifulsoup4"
            ) from exc

        book = epub.read_epub(str(self.path))
        pages: list[Page] = []

        items = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))

        page_idx = 0
        for item in items:
            soup = BeautifulSoup(item.get_content(), "html.parser")
            raw = soup.get_text(separator=" ")
            text = clean_text(raw)
            if not text:
                continue
            sentences = split_sentences(text)
            if sentences:
                title = None
                heading = soup.find(["h1", "h2", "h3"])
                if heading:
                    title = heading.get_text().strip()
                pages.append(
                    Page(
                        index=page_idx,
                        label=title if title else f"Chapter {page_idx + 1}",
                        sentences=sentences,
                        title=title,
                    )
                )
                page_idx += 1

        if not pages:
            raise ValueError("No readable text found in this EPUB file.")

        return pages
