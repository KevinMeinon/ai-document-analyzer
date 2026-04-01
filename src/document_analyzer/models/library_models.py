"""Library item domain and persistence models.

This module defines SQLModel entities and helper utilities for file-library records.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


class FileType(StrEnum):
    """Supported file types for uploaded documents."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    XLSX = "xlsx"
    UNKNOWN = "unknown"


class ProcessingStatus(StrEnum):
    """Processing lifecycle states for a library item."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    FLAGGED = "flagged"


@dataclass(kw_only=True)
class LibraryItemCreate:
    """Input model used to construct a LibraryItem.

    Args:
        filename (str): Original file name.
        size_bytes (int): File size in bytes.
        tags (list[str]): User-defined labels.
        status (ProcessingStatus): Initial processing status.
    """

    filename: str
    size_bytes: int
    tags: list[str]
    status: ProcessingStatus = ProcessingStatus.UPLOADED

    def normalized_tags(self) -> list[str]:
        """Return normalized, non-empty tags.

        Returns:
            list[str]: Lower-cased and trimmed tags.
        """
        return [clean for tag in self.tags if (clean := tag.strip().lower())]


class LibraryItem(SQLModel, table=True):
    """SQLModel table for stored library items.

    Args:
        id (UUID): Primary key.
        filename (str): Original file name.
        filetype (FileType): Inferred file type.
        size_bytes (int): File size in bytes.
        uploaded_at (datetime): Upload timestamp in UTC.
        status (ProcessingStatus): Processing status.
        tags (list[str]): Searchable item tags.
        error_message (str | None): Error details when processing fails.

    Side Effects:
        Persists records in the configured SQL database via SQLModel metadata.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str = Field(index=True, min_length=1)
    filetype: FileType = Field(default=FileType.UNKNOWN, index=True)
    size_bytes: int = Field(ge=0)
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.UPLOADED, index=True)
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    error_message: str | None = Field(default=None)
    # TODO(MVP-18): Add LightRAG document reference (e.g., lightrag_doc_id) to link metadata to retrieval memory.
    # TODO(MVP-19): Store preview/snippet fields if the original file is not persisted.

    @property
    def size_label(self) -> str:
        """Return a human-readable file-size label.

        Returns:
            str: Formatted size label.
        """
        return build_size_label(self.size_bytes)

    @classmethod
    def from_create(cls, payload: LibraryItemCreate) -> "LibraryItem":
        """Build a persisted model from a creation payload.

        Args:
            payload (LibraryItemCreate): User-provided creation data.

        Returns:
            LibraryItem: Initialized persistence model instance.
        """
        return cls(
                filename=payload.filename,
                filetype=infer_filetype(payload.filename),
                size_bytes=payload.size_bytes,
                status=payload.status,
                tags=payload.normalized_tags(),
        )


def infer_filetype(filename: str) -> FileType:
    """Infer file type from file extension.

    Args:
        filename (str): Name of the file including extension.

    Returns:
        FileType: Inferred file type enum value.
    """
    suffix = Path(filename).suffix.lower()
    match suffix:
        case ".pdf":
            return FileType.PDF
        case ".docx":
            return FileType.DOCX
        case ".txt":
            return FileType.TXT
        case ".xlsx":
            return FileType.XLSX
        case _:
            return FileType.UNKNOWN


def build_size_label(size_bytes: int) -> str:
    """Convert bytes to a readable size label.

    Args:
        size_bytes (int): File size in bytes.

    Returns:
        str: Human-readable size string.

    Raises:
        ValueError: If size_bytes is negative.
    """
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")

    match size_bytes:
        case n if n < 1024:
            return f"{n} B"
        case n if (kb := n / 1024) < 1024:
            return f"{kb:.1f} KB"
        case n if (mb := n / (1024 ** 2)) < 1024:
            return f"{mb:.1f} MB"
        case n:
            gb = n / (1024 ** 3)
            return f"{gb:.1f} GB"
