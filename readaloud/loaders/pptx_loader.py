"""PPTX loader using python-pptx."""

from __future__ import annotations

from pathlib import Path

from .base import DocumentLoader, Page
from .sentence_splitter import clean_text, split_sentences


class PptxLoader(DocumentLoader):
    """Each slide becomes one page."""

    def load(self) -> list[Page]:
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")

        try:
            from pptx import Presentation  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "python-pptx is required to read .pptx files.\n"
                "Install it with: pip install python-pptx"
            ) from exc

        prs = Presentation(str(self.path))
        pages: list[Page] = []
        total_text = 0

        for i, slide in enumerate(prs.slides):
            texts: list[str] = []
            title: str | None = None

            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    t = "".join(run.text for run in para.runs).strip()
                    if t:
                        texts.append(t)

            if texts:
                title = texts[0]

            raw = clean_text(" ".join(texts))
            if raw:
                total_text += len(raw)
                sentences = split_sentences(raw)
                if sentences:
                    pages.append(
                        Page(
                            index=i,
                            label=f"Slide {i + 1}",
                            sentences=sentences,
                            title=title,
                        )
                    )

        if total_text == 0 or not pages:
            raise ValueError("No readable text found in this PPTX file.")

        return pages
