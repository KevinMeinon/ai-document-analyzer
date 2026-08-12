"""Services for library item seeding, querying, and summary shaping."""

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import delete
from sqlmodel import Session, select

from document_analyzer.models.library_models import (
    LibraryItem,
    LibraryItemCreate,
    ProcessingStatus,
    build_size_label,
)


def create_dummy_library_items() -> list[LibraryItem]:
    # TODO(MVP-07): Delete this dummy generator once upload endpoint persists real records.
    """Create in-memory dummy library items.

    Returns:
        list[LibraryItem]: Deterministic sample items.

    Raises:
        ValueError: If one of the configured statuses is unsupported.

    """
    seed_data: list[dict[str, str | int | list[str]]] = [
            {
                    "filename": "2023_Financial_Quarterly_Audit.pdf",
                    "size_bytes": 4_404_019,
                    "status": "completed",
                    "tags": ["finance", "audit"],
            },
            {
                    "filename": "Project_Alpha_Technical_Specs.docx",
                    "size_bytes": 1_887_437,
                    "status": "processing",
                    "tags": ["technical", "product"],
            },
            {
                    "filename": "GDPR_Compliance_Contract_V4.pdf",
                    "size_bytes": 13_107_200,
                    "status": "flagged",
                    "tags": ["legal", "compliance"],
            },
    ]

    items: list[LibraryItem] = []
    for raw in seed_data:
        status_text = str(raw["status"]).lower()
        match status_text:
            case "uploaded":
                status = ProcessingStatus.UPLOADED
            case "processing":
                status = ProcessingStatus.PROCESSING
            case "completed":
                status = ProcessingStatus.COMPLETED
            case "failed":
                status = ProcessingStatus.FAILED
            case "flagged":
                status = ProcessingStatus.FLAGGED
            case _:
                raise ValueError(f"Unsupported dummy status: {status_text}")

        payload = LibraryItemCreate(
                filename=str(raw["filename"]),
                size_bytes=int(cast(int, raw["size_bytes"])),
                tags=[str(tag) for tag in cast(list[str], raw["tags"])],
                status=status,
        )
        items.append(LibraryItem.from_create(payload))

    return items


def seed_library_items(session: Session, force: bool = False) -> int:
    # TODO(MVP-08): Remove startup seeding in production path; use migrations + empty-state UX instead.
    """Seed the library table with dummy records.

    Args:
        session (Session): Open SQLModel session.
        force (bool): If true, existing rows are replaced.

    Returns:
        int: Number of inserted rows.

    Side Effects:
        Inserts and optionally deletes rows in the library table.
    """
    existing_items = session.exec(select(LibraryItem)).all()
    if existing_items and not force:
        return 0

    if force and existing_items:
        session.exec(delete(LibraryItem))
        session.commit()

    items = create_dummy_library_items()
    session.add_all(items)
    session.commit()
    return len(items)


def list_uploaded_files(session: Session, query: str = "", status: str = "all") -> list[dict]:
    # TODO(MVP-09): Return DTO/schema objects and add `file_id` to LightRAG document linkage.
    # TODO(MVP-20): When LightRAG is the source of truth for content, fetch preview/snippet data here.
    """Return uploaded files filtered by query and status.

    Args:
        session (Session): Open SQLModel session.
        query (str): Search text matched against filename and tags.
        status (str): Status filter, or "all" for no status filter.

    Returns:
        list[dict]: Filtered file records for rendering.
    """
    items = session.exec(select(LibraryItem).order_by(cast(Any, LibraryItem.uploaded_at).desc())).all()
    normalized_status = status.strip().lower()

    if normalized_status != "all":
        items = [item for item in items if item.status.value == normalized_status]

    if normalized_query := query.strip().lower():
        items = [
                item
                for item in items
                if normalized_query in item.filename.lower()
                   or any(normalized_query in tag.lower() for tag in item.tags)
        ]

    return [
            {
                    "id": str(item.id),
                    "filename": item.filename,
                    "filetype": item.filetype.value.upper(),
                    "size_label": item.size_label,
                    "uploaded_at": item.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    "status": item.status.value,
                    "tags": item.tags,
            }
            for item in items
    ]


def build_library_summary(uploaded_files: Sequence[dict]) -> dict:
    # TODO(MVP-10): Compute summary from canonical numeric size field, not parsed display labels.
    """Build aggregate summary values for the library page.

    Args:
        uploaded_files (Sequence[dict]): Records already shaped for rendering.

    Returns:
        dict: Summary payload with counts and total-storage label.
    """
    total_storage_bytes = sum(
            (int(file_size) for file in uploaded_files if
             (file_size := _parse_size_label_to_bytes(file["size_label"])) >= 0),
    )
    return {
            "total_files": len(uploaded_files),
            "total_storage_label": build_size_label(total_storage_bytes),
            "processing_count": sum(1 for file in uploaded_files if file["status"] == "processing"),
    }


def _parse_size_label_to_bytes(size_label: str) -> int:
    """Convert a size label like '4.2 MB' back to bytes.

    Args:
        size_label (str): Human-readable size label.

    Returns:
        int: Parsed size in bytes, or 0 for unsupported values.
    """
    raw = size_label.strip().upper()
    if not raw:
        return 0

    parts = raw.split()
    if len(parts) != 2:
        return 0

    value_text, unit = parts
    try:
        value = float(value_text)
    except ValueError:
        return 0

    match unit:
        case "B":
            return int(value)
        case "KB":
            return int(value * 1024)
        case "MB":
            return int(value * (1024 ** 2))
        case "GB":
            return int(value * (1024 ** 3))
        case _:
            return 0
