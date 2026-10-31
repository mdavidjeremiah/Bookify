"""Tests for DOCX, PPTX, EPUB, RTF loaders."""

from pathlib import Path
import pytest

from readaloud.loaders.docx_loader import DocxLoader
from readaloud.loaders.pptx_loader import PptxLoader
from readaloud.loaders.epub_loader import EpubLoader
from readaloud.loaders.rtf_loader import RtfLoader


def test_docx_loader(tmp_path: Path):
    try:
        from docx import Document
    except ImportError:
        pytest.skip("python-docx not installed")

    doc_path = tmp_path / "test.docx"
    doc = Document()
    doc.add_heading("Test Document Title", 0)
    doc.add_paragraph("This is the first paragraph. It contains multiple sentences.")
    doc.add_paragraph("Here is the second paragraph with another sentence.")
    doc.save(str(doc_path))

    loader = DocxLoader(doc_path)
    pages = loader.load()
    assert len(pages) >= 1
    all_sentences = [s for p in pages for s in p.sentences]
    assert any("first paragraph" in s for s in all_sentences)
    assert any("second paragraph" in s for s in all_sentences)


def test_pptx_loader(tmp_path: Path):
    try:
        from pptx import Presentation
    except ImportError:
        pytest.skip("python-pptx not installed")

    prs_path = tmp_path / "test.pptx"
    prs = Presentation()
    slide1 = prs.slides.add_slide(prs.slide_layouts[0])
    slide1.shapes.title.text = "Slide 1 Title"
    slide1.placeholders[1].text = "Slide 1 content sentence."

    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Slide 2 Title"
    slide2.placeholders[1].text = "Slide 2 body sentence."
    prs.save(str(prs_path))

    loader = PptxLoader(prs_path)
    pages = loader.load()
    assert len(pages) == 2
    assert pages[0].label == "Slide 1"
    assert pages[1].label == "Slide 2"
    assert any("Slide 1 content" in s for s in pages[0].sentences)


def test_rtf_loader(tmp_path: Path):
    rtf_path = tmp_path / "test.rtf"
    rtf_content = r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Courier;}}\f0\fs24 This is RTF text. Another sentence in RTF.}"
    rtf_path.write_text(rtf_content, encoding="utf-8")

    loader = RtfLoader(rtf_path)
    pages = loader.load()
    assert len(pages) >= 1
    all_sentences = [s for p in pages for s in p.sentences]
    assert any("This is RTF text" in s for s in all_sentences)


def test_pdf_loader_empty_scanned_error(tmp_path: Path):
    import pypdf
    from readaloud.loaders.pdf_loader import PdfLoader

    pdf_path = tmp_path / "blank.pdf"
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with open(pdf_path, "wb") as f:
        writer.write(f)

    loader = PdfLoader(pdf_path)
    with pytest.raises(ValueError, match="OCR support is planned for v2"):
        loader.load()
