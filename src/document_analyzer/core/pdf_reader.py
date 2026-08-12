"""PDF text extraction with a local OCR fallback for scanned pages."""

import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from pdfreader import SimplePDFViewer

from document_analyzer.core.settings import Settings, get_settings


class PdfReadError(RuntimeError):
    """Raised when a PDF cannot be opened or text cannot be extracted."""


@dataclass(frozen=True, slots=True)
class PdfPage:
    """Extracted text and number for one PDF page."""

    number: int
    text: str


@dataclass(frozen=True, slots=True)
class PdfDocument:
    """A retained PDF and its extracted, page-aware text."""

    path: Path
    filename: str
    metadata: dict[str, str]
    pages: tuple[PdfPage, ...]
    file_type: str = "pdf"

    @property
    def document_id(self) -> str:
        return self.metadata.get("document_id", self.path.name)

    @property
    def content(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


def read_pdf(path: str | Path, settings: Settings | None = None) -> PdfDocument:
    """Extract native PDF text and OCR pages with no text when configured."""

    pdf_path = Path(path)
    runtime_settings = settings or get_settings()
    logger.debug("Started reading PDF {}", pdf_path)
    if not pdf_path.is_file():
        logger.warning("Could not read PDF because it does not exist: {}", pdf_path)
        raise PdfReadError(f"PDF does not exist: {pdf_path}")

    try:
        with pdf_path.open("rb") as file:
            viewer = SimplePDFViewer(file)
            pages = [
                PdfPage(
                    number=page_number,
                    text="".join(str(value) for value in getattr(canvas, "strings", [])).strip(),
                )
                for page_number, canvas in enumerate(viewer, start=1)
            ]
    except Exception as exc:
        logger.exception("PDF reading failed for {} with {}", pdf_path, type(exc).__name__)
        raise PdfReadError(f"Unable to read PDF {pdf_path}: {exc}") from exc

    if not pages:
        logger.warning("PDF contains no pages: {}", pdf_path)
        raise PdfReadError(f"PDF contains no pages: {pdf_path}")

    native_page_count = sum(bool(page.text) for page in pages)
    ocr_page_count = 0
    ocr_failures = 0
    if runtime_settings.ocr_enabled:
        updated_pages: list[PdfPage] = []
        for page in pages:
            if page.text:
                updated_pages.append(page)
                continue
            try:
                ocr_text = _ocr_page(pdf_path, page.number, runtime_settings)
            except PdfReadError as exc:
                ocr_failures += 1
                logger.warning("OCR failed for page {}: {}", page.number, exc)
                ocr_text = ""
            if ocr_text:
                ocr_page_count += 1
            updated_pages.append(PdfPage(number=page.number, text=ocr_text))
        pages = updated_pages

    if not any(page.text for page in pages):
        reason = "no_extractable_text"
        if ocr_failures:
            reason = "native_text_empty_and_ocr_failed"
        logger.warning("PDF has no usable text ({}) : {}", reason, pdf_path)
        raise PdfReadError(f"PDF contains no extractable text: {pdf_path}")

    stat = pdf_path.stat()
    extraction_method = "mixed" if native_page_count and ocr_page_count else "ocr" if ocr_page_count else "text"
    metadata = {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "size_bytes": str(stat.st_size),
        "extraction_method": extraction_method,
        "native_page_count": str(native_page_count),
        "ocr_page_count": str(ocr_page_count),
    }
    document = PdfDocument(path=pdf_path, filename=pdf_path.name, metadata=metadata, pages=tuple(pages))
    logger.info(
        "Read PDF {}: {} pages, {} native-text pages, {} OCR pages, {} characters ({})",
        pdf_path,
        len(document.pages),
        native_page_count,
        ocr_page_count,
        len(document.content),
        extraction_method,
    )
    return document


def _ocr_page(path: Path, page_number: int, settings: Settings) -> str:
    """Render and OCR one page using bundled Python package runtimes."""

    started = time.perf_counter()
    try:
        import pypdfium2 as pdfium
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise PdfReadError("OCR dependencies are unavailable; run uv sync to install them") from exc

    try:
        pdf = pdfium.PdfDocument(str(path))
        page = pdf[page_number - 1]
        bitmap = page.render(scale=settings.ocr_dpi / 72)
        result, _elapsed = RapidOCR()(bitmap.to_pil())
    except Exception as exc:
        raise PdfReadError(f"OCR failed on page {page_number}: {exc}") from exc

    text = "\n".join(str(item[1]) for item in (result or []) if len(item) > 1 and item[1]).strip()
    logger.info(
        "OCR completed for page {}: {} characters in {:.2f} ms",
        page_number,
        len(text),
        (time.perf_counter() - started) * 1000,
    )
    return text
