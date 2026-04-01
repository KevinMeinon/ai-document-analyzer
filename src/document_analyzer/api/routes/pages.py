from asyncio import sleep

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import HTMLResponse

from document_analyzer.core.db_connection import SessionDep
from document_analyzer.services.library_service import (
    build_library_summary,
    list_uploaded_files,
)

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def dashboard(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"active_page": "dashboard"},
    )


@router.post("/analyze", response_class=HTMLResponse, name="analyze_file")
async def analyze_file(file: UploadFile = File(...)) -> HTMLResponse:
    # TODO(MVP-03): Replace placeholder delay with real upload pipeline:
    # validate -> parse -> insert into LightRAG -> persist metadata -> return file_id-aware response.
    # TODO(MVP-21): Do not persist raw files to an upload folder; store only metadata + LightRAG memory.
    """Simulate a file analysis request.

    Args:
        file (UploadFile): Uploaded file payload.

    Returns:
        HTMLResponse: Minimal HTML fragment for HTMX target replacement.

    Side Effects:
        Introduces an artificial 5-second delay to mimic processing latency.
    """
    await sleep(5)
    return HTMLResponse(
            content=(
                    f"<div class=\"alert alert-success mb-0\">"
                    f"Analysis placeholder complete for <strong>{file.filename}</strong>."
                    f"</div>"
            ),
    )


@router.get("/base", response_class=HTMLResponse, name="base")
async def base(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request=request, name="base.html")


@router.get("/details/{file_id}", response_class=HTMLResponse, name="details")
async def details(request: Request, file_id: str) -> HTMLResponse:
    # TODO(MVP-04): Resolve file metadata + retrieval context by file_id from DB/LightRAG and pass into template.
    templates = request.app.state.templates
    return templates.TemplateResponse(
            request=request,
            name="details.html",
            context={
                    "active_page": "details",
                    "file_id": file_id,
            },
    )


@router.get("/library", response_class=HTMLResponse, name="library")
async def library(request: Request, session: SessionDep) -> HTMLResponse:
    # TODO(MVP-05): Source library rows from real uploaded/ingested records, not seeded demo data.
    templates = request.app.state.templates
    uploaded_files = list_uploaded_files(session=session)
    return templates.TemplateResponse(
            request=request,
            name="library.html",
            context={
                    "active_page": "library",
                    "uploaded_files": uploaded_files,
                    "library_summary": build_library_summary(uploaded_files),
            },
    )


@router.get("/library/list", response_class=HTMLResponse, name="library_list")
async def library_list(
        request: Request,
        session: SessionDep,
        q: str = Query(default=""),
        status: str = Query(default="all"),
) -> HTMLResponse:
    # TODO(MVP-06): Keep filtering contract, but back it with real persisted metadata and pagination.
    templates = request.app.state.templates
    filtered_files = list_uploaded_files(session=session, query=q, status=status)
    return templates.TemplateResponse(
            request=request,
            name="partials/library_list.html",
            context={"uploaded_files": filtered_files},
    )
