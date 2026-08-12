"""Database connection and session utilities."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

# TODO(MVP-11): Move DB URL and engine settings into a typed settings module (pydantic-settings).
# TODO(MVP-33): Add migration strategy (Alembic or SQLModel migration path) for schema evolution.
sqlite_file_name = "db.sqlite3"
sqlite_url = f"sqlite:///{sqlite_file_name}"

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
