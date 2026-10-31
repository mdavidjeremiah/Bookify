"""Sentence splitting and text cleaning utilities."""

from __future__ import annotations

import re
from typing import Callable


def _make_pysbd_splitter() -> Callable[[str], list[str]]:
    try:
        import pysbd  # type: ignore

        seg = pysbd.Segmenter(language="en", clean=True)

        def _split(text: str) -> list[str]:
            return [s.strip() for s in seg.segment(text) if s.strip()]

        return _split
    except ImportError:
        return _regex_split


# Regex fallback handling common abbreviations
_ABBR_PATTERN = re.compile(
    r"\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.e|vol|no|pp|fig|al|st|dept)\.\s*$",
    re.IGNORECASE,
)
_SPLIT_PATTERN = re.compile(r'(?:(?<=[.!?])|(?<=[.!?]["\']))\s+(?=[A-Z0-9"\'(])')


def _regex_split(text: str) -> list[str]:
    raw_parts = _SPLIT_PATTERN.split(text)
    out: list[str] = []
    buffer = ""

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if buffer:
            buffer += " " + part
        else:
            buffer = part

        # If buffer ends with an abbreviation like "Dr." or "Mr.", don't split yet
        if _ABBR_PATTERN.search(buffer):
            continue

        out.append(buffer)
        buffer = ""

    if buffer:
        out.append(buffer)
    return out


_splitter: Callable[[str], list[str]] | None = None


def split_sentences(text: str) -> list[str]:
    """Split *text* into a list of sentences."""
    global _splitter
    if _splitter is None:
        _splitter = _make_pysbd_splitter()
    return _splitter(text)


def clean_text(text: str) -> str:
    """
    Clean raw extracted text before speaking:
    - strip hyphenated line breaks (e.g. "con-\nnection" -> "connection")
    - strip standalone page numbers (e.g. line with just numbers)
    - collapse excessive whitespace and newlines
    """
    if not text:
        return ""

    # Dehyphenate line breaks (e.g., "infor-\nmation" -> "information")
    text = re.sub(r"(\b\w+)-\s*\n\s*(\w+\b)", r"\1\2", text)

    # Remove standalone page numbers or Roman numerals on single lines
    text = re.sub(r"(?m)^\s*(?:\d+|[ivxlcdm]+)\s*$", "", text, flags=re.IGNORECASE)

    # Collapse repeated line breaks into single breaks
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Convert remaining single newlines to spaces (join wrapped lines within paragraphs)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    # Collapse horizontal spaces
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse multiple consecutive newlines
    text = re.sub(r"\n+", " ", text)

    return text.strip()
