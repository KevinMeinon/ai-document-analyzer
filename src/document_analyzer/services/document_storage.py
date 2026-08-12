"""Safe retention of uploaded originals."""

from pathlib import Path
from uuid import UUID, uuid4

from loguru import logger

from document_analyzer.core.document_reader import SUPPORTED_EXTENSIONS
from document_analyzer.core.settings import Settings


def store_uploaded_file(
    filename: str,
    content: bytes,
    settings: Settings,
    document_id: UUID | None = None,
) -> tuple[UUID, Path]:
    """Store an upload below the configured directory using a generated ID."""

    safe_name = Path(filename).name
    suffix = Path(safe_name).suffix.lower()
    if not safe_name or suffix not in SUPPORTED_EXTENSIONS:
        logger.warning("Rejected upload {} because its extension is unsupported", safe_name or "[missing]")
        raise ValueError("Only PDF, DOCX, DOC, TXT, and MD files are supported")
    if not content:
        logger.warning("Rejected upload {} because it is empty", safe_name)
        raise ValueError("Uploaded document is empty")
    if len(content) > settings.max_upload_size_bytes:
        logger.warning(
            "Rejected upload {} because it contains {} bytes and exceeds the size limit", safe_name, len(content)
        )
        raise ValueError(f"Document exceeds the {settings.max_upload_size_bytes // (1024 * 1024)} MB limit")

    identifier = document_id or uuid4()
    target_directory = settings.upload_dir / str(identifier)
    target_directory.mkdir(parents=True, exist_ok=True)
    target = target_directory / safe_name
    target.write_bytes(content)
    logger.debug("Persisted upload {} at {}", identifier, target)
    return identifier, target
