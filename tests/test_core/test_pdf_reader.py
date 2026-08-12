import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from document_analyzer.core import pdf_reader
from document_analyzer.core.pdf_reader import PdfReadError, read_pdf
from document_analyzer.core.settings import Settings


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


def test_ocr_page_renders_and_extracts_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"pdf")

    class FakePdf:
        def __init__(self, path: str):
            self.path = path

        def __getitem__(self, index: int):
            return SimpleNamespace(render=lambda scale: SimpleNamespace(to_pil=lambda: object()))

    class FakeRapidOCR:
        def __call__(self, image: object):
            return ([[[0, 0], "Recognized text", 0.9]], 0.1)

    monkeypatch.setitem(sys.modules, "pypdfium2", ModuleType("pypdfium2"))
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", ModuleType("rapidocr_onnxruntime"))
    sys.modules["pypdfium2"].PdfDocument = FakePdf  # type: ignore[attr-defined]
    sys.modules["rapidocr_onnxruntime"].RapidOCR = FakeRapidOCR  # type: ignore[attr-defined]

    assert pdf_reader._ocr_page(source, 1, Settings()) == "Recognized text"


def test_ocr_page_reports_missing_tools(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "pypdfium2", None)
    monkeypatch.setitem(sys.modules, "rapidocr_onnxruntime", None)

    with pytest.raises(PdfReadError, match="OCR dependencies are unavailable"):
        pdf_reader._ocr_page(tmp_path / "scan.pdf", 1, Settings())
