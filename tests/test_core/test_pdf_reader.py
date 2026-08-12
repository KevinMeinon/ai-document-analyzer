from pathlib import Path

import pytest

from document_analyzer.core.pdf_reader import PdfReadError, read_pdf


def test_read_pdf_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(PdfReadError, match="does not exist"):
        read_pdf(tmp_path / "missing.pdf")


def test_read_pdf_rejects_invalid_file(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.pdf"
    invalid.write_bytes(b"not a PDF")
    with pytest.raises(PdfReadError):
        read_pdf(invalid)


def test_sample_pdf_extracts_text_from_all_pages() -> None:
    document = read_pdf(Path("src/document_analyzer/core/sample.pdf"))

    assert len(document.pages) == 12
    assert all(page.text for page in document.pages)
    assert "Abwässerschäden" in document.content
