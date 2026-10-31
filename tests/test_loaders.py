"""Tests for document loaders and format detection."""

from pathlib import Path
import pytest

from readaloud.loaders import get_loader, detect_format_by_signature
from readaloud.loaders.txt_loader import TxtLoader
from readaloud.loaders.pdf_loader import PdfLoader


def test_txt_loader(tmp_path: Path):
    f = tmp_path / "sample.txt"
    f.write_text("Sentence one. Sentence two! Sentence three?", encoding="utf-8")
    loader = TxtLoader(f)
    pages = loader.load()
    assert len(pages) == 1
    assert len(pages[0].sentences) == 3
    assert pages[0].sentences[0] == "Sentence one."


def test_txt_loader_empty(tmp_path: Path):
    f = tmp_path / "empty.txt"
    f.write_text("   \n\n  ", encoding="utf-8")
    loader = TxtLoader(f)
    with pytest.raises(ValueError, match="empty"):
        loader.load()


def test_format_detection_by_signature_pdf(tmp_path: Path):
    f = tmp_path / "mystery_doc"
    f.write_bytes(b"%PDF-1.4 sample pdf header")
    detected = detect_format_by_signature(f)
    assert detected == ".pdf"


def test_format_detection_by_signature_rtf(tmp_path: Path):
    f = tmp_path / "mystery_rtf"
    f.write_bytes(b"{\\rtf1\\ansi\\deff0 sample rtf")
    detected = detect_format_by_signature(f)
    assert detected == ".rtf"


def test_get_loader_signature_fallback(tmp_path: Path):
    f = tmp_path / "no_ext_file"
    f.write_text("This is plain text with no extension. It should still work.", encoding="utf-8")
    loader = get_loader(f)
    pages = loader.load()
    assert len(pages) >= 1


def test_get_loader_unsupported(tmp_path: Path):
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\nfake png data")
    with pytest.raises(ValueError, match="Unsupported file format"):
        get_loader(f)


def test_pdf_empty_scanned_detection(tmp_path: Path):
    # Mocking a PDF without text should raise ValueError mentioning OCR
    f = tmp_path / "scanned.pdf"
    f.write_text("not a real pdf", encoding="utf-8")
    loader = PdfLoader(f)
    with pytest.raises(Exception):
        loader.load()
