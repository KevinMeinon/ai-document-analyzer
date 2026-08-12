"""Tailwind/HTMX page routes for uploading, analyzing, and archiving documents."""

from pathlib import Path
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from loguru import logger
from sqlmodel import Session, select

from document_analyzer.core.db_connection import SessionDep
from document_analyzer.core.document_reader import document_from_extracted_pages, read_document
from document_analyzer.core.pdf_reader import PdfDocument, PdfReadError
from document_analyzer.core.settings import get_settings
from document_analyzer.models.library_models import FileType, LibraryItem, ProcessingStatus, infer_filetype
from document_analyzer.services.chroma_service import ChromaDocumentStore
from document_analyzer.services.document_storage import store_uploaded_file
from document_analyzer.services.llm_service import analyze_document

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    logger.debug("landing_page_rendered")
    return _template(request, "dashboard.html", {"active_page": "home"})


@router.post("/documents/upload", response_class=HTMLResponse, name="upload_document")
async def upload_document(
    request: Request,
    session: SessionDep,
    file: Annotated[UploadFile, File(...)],
) -> Response:
    settings = get_settings()
    filename = file.filename or ""
    logger.info(
        "Upload received: {} ({}, {} bytes)",
        Path(filename).name or "[missing]",
        file.content_type or "-",
        file.size if file.size is not None else "-",
    )
    try:
        content = await file.read()
        logger.debug("Read {} bytes from upload {}", len(content), Path(filename).name or "[missing]")
        document_id, path = store_uploaded_file(filename, content, settings)
        logger.info("Stored upload {} at {}", document_id, path)
        item = LibraryItem(
            id=document_id,
            filename=Path(filename).name,
            filetype=infer_filetype(filename),
            size_bytes=len(content),
            status=ProcessingStatus.PROCESSING,
            storage_path=str(path),
        )
        session.add(item)
        session.commit()
        logger.debug("Created document record {} with status {}", document_id, item.status.value)

        logger.info("Started extraction for {} ({})", document_id, path.suffix.lower())
        document = read_document(path, settings)
        logger.info("Extracted {} pages for {}", len(document.pages), document_id)
        document.metadata["document_id"] = str(document_id)
        item.extracted_pages = [page.text for page in document.pages]
        item.extraction_metadata = dict(document.metadata)
        item.page_count = len(document.pages)
        session.add(item)
        session.commit()
        logger.info(
            "Persisted extracted text for {} ({} pages, {} characters)",
            document_id,
            len(item.extracted_pages),
            len(document.content),
        )
        logger.info("Started vector indexing for {}", document_id)
        store = ChromaDocumentStore(settings)
        chunk_count = store.ingest(document)
        logger.info("Indexed {} chunks for {}", chunk_count, document_id)
        item.status = ProcessingStatus.COMPLETED
        session.add(item)
        session.commit()
        logger.info("Document {} processing completed with status {}", document_id, item.status.value)
    except (ValueError, PdfReadError, OSError) as exc:
        logger.warning(
            "Document {} was rejected due to {}: {}",
            locals().get("document_id", "-"),
            type(exc).__name__,
            exc,
        )
        _mark_failed(session, locals().get("item"), str(exc))
        return _template(request, "partials/upload_error.html", {"error": str(exc)}, status_code=422)
    except Exception as exc:
        logger.exception(
            "Document {} processing failed with {}",
            locals().get("document_id", "-"),
            type(exc).__name__,
        )
        _mark_failed(session, locals().get("item"), str(exc))
        return _template(request, "partials/upload_error.html", {"error": "Document analysis failed."}, status_code=503)

    return Response(status_code=204, headers={"HX-Redirect": f"/documents/{document_id}"})


@router.get("/documents/{document_id}", response_class=HTMLResponse, name="document_analysis")
async def document_analysis(request: Request, document_id: UUID, session: SessionDep) -> HTMLResponse:
    logger.info("Analysis page requested for {}", document_id)
    item = _get_item(session, document_id)
    document = _document_for_item(item, session)
    return _template(
        request,
        "analysis.html",
        {"active_page": "analysis", "document": item, "extracted": document},
    )


@router.post("/documents/{document_id}/chat", response_class=HTMLResponse, name="document_chat")
async def document_chat(
    request: Request,
    document_id: UUID,
    session: SessionDep,
    prompt: Annotated[str, Form(...)],
    intent: Annotated[str, Form()] = "chat",
) -> HTMLResponse:
    item = _get_item(session, document_id)
    if not item.storage_path:
        raise HTTPException(status_code=422, detail="Document has no retained file")
    settings = get_settings()
    logger.info("Chat started for {} with a {} character prompt", document_id, len(prompt))
    try:
        if intent == "summary" and item.summary:
            logger.info("Returning cached summary for {}", document_id)
            return _template(
                request,
                "partials/chat_message.html",
                {"answer": item.summary, "sources": [], "is_error": False},
            )
        document = _document_for_item(item, session)
        result = await analyze_document(document, prompt, ChromaDocumentStore(settings), settings)
        if intent == "summary":
            item.summary = result.answer
            session.add(item)
            session.commit()
            logger.info("Cached generated summary for {}", document_id)
    except Exception as exc:
        logger.exception("Chat failed for {} with {}", document_id, type(exc).__name__)
        return _template(request, "partials/chat_message.html", {"error": str(exc), "is_error": True}, status_code=503)
    logger.info("Chat completed for {} using {} sources", document_id, len(result.sources))
    return _template(
        request,
        "partials/chat_message.html",
        {"answer": result.answer, "sources": result.sources, "is_error": False},
    )


@router.get("/archive", response_class=HTMLResponse, name="archive")
async def archive(request: Request, session: SessionDep) -> HTMLResponse:
    documents = _list_documents(session)
    logger.info("Archive page rendered with {} documents", len(documents))
    return _template(request, "archive.html", {"active_page": "archive", "documents": documents})


@router.get("/archive/list", response_class=HTMLResponse, name="archive_list")
async def archive_list(request: Request, session: SessionDep, q: str = "") -> HTMLResponse:
    documents = _list_documents(session, q)
    logger.debug("Archive search returned {} documents for a {} character query", len(documents), len(q))
    return _template(request, "partials/archive_list.html", {"documents": documents})


@router.get("/documents/{document_id}/file", name="document_file")
async def document_file(document_id: UUID, session: SessionDep) -> FileResponse:
    item = _get_item(session, document_id)
    if not item.storage_path or not Path(item.storage_path).is_file():
        raise HTTPException(status_code=404, detail="Retained document not found")
    media_types = {
        FileType.PDF: "application/pdf",
        FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        FileType.DOC: "application/msword",
        FileType.TXT: "text/plain",
        FileType.MD: "text/markdown",
    }
    logger.debug("Served original file for {} ({})", document_id, item.filetype.value)
    return FileResponse(item.storage_path, media_type=media_types.get(item.filetype, "application/octet-stream"))


def _template(request: Request, name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)


def _get_item(session: Session, document_id: UUID) -> LibraryItem:
    item = session.get(LibraryItem, document_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return item


def _list_documents(session: Session, query: str = "") -> list[LibraryItem]:
    documents = session.exec(
        select(LibraryItem)
        .where(LibraryItem.status == ProcessingStatus.COMPLETED)
        .order_by(
            cast(Any, LibraryItem.uploaded_at).desc(),
        ),
    ).all()
    normalized = query.strip().lower()
    if normalized:
        documents = [document for document in documents if normalized in document.filename.lower()]
    return list(documents)


def _mark_failed(session: Session, item: LibraryItem | None, message: str) -> None:
    if item is None:
        return
    item.status = ProcessingStatus.FAILED
    item.error_message = message[:1000]
    session.add(item)
    session.commit()
    logger.info("Marked document {} as failed; error length is {} characters", item.id, len(message))


def _document_for_item(item: LibraryItem, session: Session) -> PdfDocument:
    """Return persisted extraction, backfilling records created before this field existed."""
    if not item.storage_path:
        raise HTTPException(status_code=422, detail="Document has no retained file")
    if item.extracted_pages:
        logger.debug("Loaded persisted extraction for {} ({} pages)", item.id, len(item.extracted_pages))
        return document_from_extracted_pages(
            item.storage_path,
            item.filename,
            item.filetype.value,
            item.extracted_pages,
            {**item.extraction_metadata, "document_id": str(item.id)},
        )

    logger.info("No persisted extraction for {}; reading original once to backfill", item.id)
    document = read_document(item.storage_path, get_settings())
    document.metadata["document_id"] = str(item.id)
    item.extracted_pages = [page.text for page in document.pages]
    item.extraction_metadata = dict(document.metadata)
    item.page_count = len(document.pages)
    session.add(item)
    session.commit()
    logger.info("Backfilled persisted extraction for {} ({} pages)", item.id, len(item.extracted_pages))
    return document
