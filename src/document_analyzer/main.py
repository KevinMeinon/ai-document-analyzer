from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from document_analyzer.api.routes.pages import router as pages_router
from document_analyzer.core.db_connection import create_db_and_tables, engine
from document_analyzer.services.library_service import seed_library_items

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.state.templates = Jinja2Templates(directory=TEMPLATES_DIR)

app.include_router(pages_router)


@app.on_event("startup")
def on_startup() -> None:
    # TODO(MVP-01): Remove dummy seed usage once real upload->parse->LightRAG ingest is implemented.
    # TODO(MVP-02): Add settings-driven startup wiring for LightRAG client and LLM provider dependencies.
    """Initialize schema and seed dummy library records on startup.

    Side Effects:
        Creates DB tables and inserts dummy library items when table is empty.
    """
    create_db_and_tables()
    with Session(engine) as session:
        seed_library_items(session=session)


def main() -> None:
    """CLI entrypoint used by the console script."""
    import uvicorn

    uvicorn.run("document_analyzer.main:app", host="0.0.0.0", port=8000, reload=True)
