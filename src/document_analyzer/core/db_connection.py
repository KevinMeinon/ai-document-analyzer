"""Database connection and session utilities."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from document_analyzer.core.settings import get_settings

# TODO(MVP-33): Add migration strategy (Alembic or SQLModel migration path) for schema evolution.
database_path = get_settings().database_path
database_path.parent.mkdir(parents=True, exist_ok=True)
sqlite_url = f"sqlite:///{database_path}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create database tables registered in SQLModel metadata.

    Side Effects:
        Creates tables in the configured SQLite database.
    """
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        existing_columns = {column["name"] for column in inspect(engine).get_columns("libraryitem")}
        migrations = {
            "storage_path": "TEXT",
            "page_count": "INTEGER NOT NULL DEFAULT 0",
            "summary": "TEXT",
            "extracted_pages": "TEXT NOT NULL DEFAULT '[]'",
            "extraction_metadata": "TEXT NOT NULL DEFAULT '{}'",
        }
        for column, definition in migrations.items():
            if column not in existing_columns:
                connection.execute(text(f"ALTER TABLE libraryitem ADD COLUMN {column} {definition}"))


def get_session() -> Generator[Session]:
    """Yield a database session.

    Yields:
        Session: SQLModel database session.
    """
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
