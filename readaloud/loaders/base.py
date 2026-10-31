"""Base classes for document loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Page:
    """A logical page/slide/chapter with its sentences."""

    index: int  # 0-based
    label: str  # human-readable, e.g. "Page 3" or "Chapter 2"
    sentences: list[str] = field(default_factory=list)
    title: Optional[str] = None

    def __bool__(self) -> bool:
        return bool(self.sentences)


class DocumentLoader(ABC):
    """Abstract base class for all document loaders."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    @abstractmethod
    def load(self) -> list[Page]:
        """
        Extract and return all pages with their sentences.

        Raises:
            ValueError: if the file has no extractable text (e.g. scanned PDF).
            FileNotFoundError: if the path doesn't exist.
        """

    @property
    def name(self) -> str:
        return self.path.name
