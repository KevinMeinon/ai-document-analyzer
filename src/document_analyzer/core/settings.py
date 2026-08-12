"""Application settings."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Configuration for PDF storage, ChromaDB, and model services."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_model: str = "openai:gpt-5-nano"
    chroma_path: Path = Path(".data/chroma")
    chroma_collection: str = "pdf_documents"
    sample_pdf_path: Path = Path("src/document_analyzer/core/sample.pdf")
    upload_dir: Path = Path(".data/uploads")
    max_upload_size_bytes: int = 50 * 1024 * 1024
    libreoffice_command: str = "soffice"
    conversion_timeout_seconds: int = 60
    log_level: str = "INFO"
    log_file: Path = Path(".data/logs/app.log")
    log_rotation: str = "10 MB"
    log_retention: str = "14 days"
    chunk_size: int = 1800
    chunk_overlap: int = 250
    retrieval_limit: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
