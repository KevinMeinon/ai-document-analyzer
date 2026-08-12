import argparse
import asyncio
import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger

from document_analyzer.api.routes.api import router as api_router
from document_analyzer.api.routes.pages import router as pages_router
from document_analyzer.core.db_connection import create_db_and_tables
from document_analyzer.core.logging import configure_logging
from document_analyzer.core.pdf_reader import PdfReadError, read_pdf
from document_analyzer.core.settings import Settings, get_settings
from document_analyzer.services.chroma_service import ChromaDocumentStore
from document_analyzer.services.llm_service import analyze_document

settings = get_settings()
configure_logging(settings)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Initialize application persistence before serving requests."""
    logger.info("application_startup_begin")
    create_db_and_tables()
    logger.info("application_startup_complete")
    yield
    logger.info("application_shutdown")


app = FastAPI(lifespan=lifespan)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.include_router(pages_router)
app.include_router(api_router)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with a correlation ID and elapsed time."""

    request_id = request.headers.get("x-request-id") or uuid4().hex
    started = time.perf_counter()
    with logger.contextualize(request_id=request_id):
        logger.info(
            "request_started method={} path={} content_type={} content_length={} htmx={}",
            request.method,
            request.url.path,
            request.headers.get("content-type", "-"),
            request.headers.get("content-length", "-"),
            request.headers.get("hx-request", "false"),
        )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed method={} path={}", request.method, request.url.path)
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed method={} path={} status={} elapsed_ms={:.2f}",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, exc: RequestValidationError):
    """Expose safe validation details for HTMX and JSON clients."""

    errors = [
        {
            "location": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    logger.warning(
        "request_validation_failed path={} content_type={} errors={}",
        request.url.path,
        request.headers.get("content-type", "-"),
        errors,
    )
    request_id = request.headers.get("x-request-id", "-")
    if request.headers.get("hx-request", "false").lower() == "true":
        message = "; ".join(f"{error['location']}: {error['message']}" for error in errors)
        templates = request.app.state.templates
        return templates.TemplateResponse(
            request=request,
            name="partials/upload_error.html",
            context={"error": f"Upload validation failed: {message}"},
            status_code=422,
            headers={"X-Request-ID": request_id},
        )
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
        headers={"X-Request-ID": request_id},
    )


async def chat_loop(
    settings: Settings | None = None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> None:
    """Run an interactive chat against the retained sample PDF."""
    settings = settings or get_settings()
    document = read_pdf(settings.sample_pdf_path)
    store = ChromaDocumentStore(settings)
    store.ingest(document)

    output_fn(f"Chatting about {document.filename}. Type 'summary' for a summary or 'exit' to leave.")
    while True:
        try:
            question = input_fn("you> ").strip()
        except EOFError:
            output_fn("")
            break

        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        if question.lower() == "summary":
            question = "Summarize this PDF and identify its key points."

        try:
            result = await analyze_document(document, question, store, settings)
        except Exception as exc:
            output_fn(f"error> {exc}")
            continue

        output_fn(f"assistant> {result.answer}")
        if result.sources:
            output_fn(f"sources> {', '.join(result.sources)}")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI document analyzer")
    parser.add_argument(
        "command",
        choices=("serve", "chat"),
        nargs="?",
        default="serve",
        help="run the web server (default) or chat with the sample PDF",
    )
    parser.add_argument("--host", default="0.0.0.0", help=argparse.SUPPRESS)
    parser.add_argument("--port", default=8001, type=int, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entrypoint used by the console script."""
    args = _parse_args(argv)
    if args.command == "chat":
        try:
            asyncio.run(chat_loop())
        except (PdfReadError, ValueError) as exc:
            raise SystemExit(f"Unable to start PDF chat: {exc}") from exc
        return

    import uvicorn

    uvicorn.run("document_analyzer.main:app", host=args.host, port=args.port, reload=True)


if __name__ == "__main__":
    main()
