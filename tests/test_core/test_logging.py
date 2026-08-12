import asyncio
from pathlib import Path

from loguru import logger

from document_analyzer.core.logging import configure_logging
from document_analyzer.core.settings import Settings


def test_configure_logging_creates_file_sink(tmp_path: Path) -> None:
    log_path = tmp_path / "logs" / "app.log"
    configure_logging(Settings(log_file=log_path))
    logger.info("logging_test_marker")
    asyncio.run(logger.complete())

    assert log_path.exists()
    assert "logging_test_marker" in log_path.read_text(encoding="utf-8")
