"""JSON API for the sample PDF analysis workflow."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from document_analyzer.core.pdf_reader import PdfReadError, read_pdf
from document_analyzer.core.settings import get_settings
from document_analyzer.services.chroma_service import ChromaDocumentStore
from document_analyzer.services.llm_service import PdfAnalysisResult, analyze_document

router = APIRouter(prefix="/api/documents/sample", tags=["documents"])


class IngestResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks: int
    retained_path: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)


def _sample_document():
    settings = get_settings()
    try:
        return settings, read_pdf(Path(settings.sample_pdf_path))
    except PdfReadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/ingest", response_model=IngestResponse)
def ingest_sample() -> IngestResponse:
    settings, document = _sample_document()
    try:
        chunks = ChromaDocumentStore(settings).ingest(document)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return IngestResponse(
        document_id=document.document_id,
        filename=document.filename,
        pages=len(document.pages),
        chunks=chunks,
        retained_path=str(document.path),
    )


@router.post("/summary", response_model=PdfAnalysisResult)
async def summarize_sample() -> PdfAnalysisResult:
    settings, document = _sample_document()
    try:
        store = ChromaDocumentStore(settings)
        store.ingest(document)
        return await analyze_document(document, "Summarize this PDF and identify its key points.", store, settings)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/question", response_model=PdfAnalysisResult)
async def question_sample(request: QuestionRequest) -> PdfAnalysisResult:
    settings, document = _sample_document()
    try:
        store = ChromaDocumentStore(settings)
        store.ingest(document)
        return await analyze_document(document, request.question, store, settings)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
