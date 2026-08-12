"""PDF extraction using :mod:`pdfreader` only."""

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from pdfreader import SimplePDFViewer


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
        return self.path.name

    @property
    def content(self) -> str:
        return "\n\n".join(page.text for page in self.pages if page.text)


def read_pdf(path: str | Path) -> PdfDocument:
    """Read a PDF with pdfreader and return its extracted text.

    ``PdfReadError`` deliberately wraps every input/extraction failure so API
    callers do not need to know which parser exception was raised internally.
    """

    pdf_path = Path(path)
    logger.debug("pdf_read_started path={}", pdf_path)
    if not pdf_path.is_file():
        logger.warning("pdf_read_rejected reason=missing_file path={}", pdf_path)
        raise PdfReadError(f"PDF does not exist: {pdf_path}")

    try:
        with pdf_path.open("rb") as file:
            viewer = SimplePDFViewer(file)
            pages: list[PdfPage] = []
            for page_number, canvas in enumerate(viewer, start=1):
                # The iterator yields a copy of each page canvas. Reading
                # viewer.canvas after advancing the iterator returns only the
                # final page.
                text = "".join(str(value) for value in getattr(canvas, "strings", [])).strip()
                pages.append(PdfPage(number=page_number, text=text))
    except Exception as exc:
        logger.exception("pdf_read_failed path={} exception_type={}", pdf_path, type(exc).__name__)
        raise PdfReadError(f"Unable to read PDF {pdf_path}: {exc}") from exc

    if not pages or not any(page.text for page in pages):
        logger.warning("pdf_read_rejected reason=no_extractable_text path={}", pdf_path)
        raise PdfReadError(f"PDF contains no extractable text: {pdf_path}")

    stat = pdf_path.stat()
    metadata = {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "size_bytes": str(stat.st_size),
    }
    document = PdfDocument(
        path=pdf_path,
        filename=pdf_path.name,
        metadata=metadata,
        pages=tuple(pages),
    )
    logger.info(
        "pdf_read_completed path={} page_count={} character_count={}",
        pdf_path,
        len(document.pages),
        len(document.content),
    )
    return document
