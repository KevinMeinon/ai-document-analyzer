"""Centralized Loguru configuration and request context helpers."""

import logging as standard_logging
import sys
from pathlib import Path

from loguru import logger

from document_analyzer.core.settings import Settings


class InterceptHandler(standard_logging.Handler):
    """Forward standard-library logs, including Uvicorn logs, to Loguru."""

    def emit(self, record: standard_logging.LogRecord) -> None:
        level = record.levelname
        try:
            logger.opt(exception=record.exc_info).log(level, record.getMessage())
        except ValueError:
            logger.opt(exception=record.exc_info).log("INFO", record.getMessage())


def configure_logging(settings: Settings) -> None:
    """Configure console and rotating-file diagnostics exactly once per process."""

    log_path: Path = settings.log_file
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.configure(extra={"request_id": "-"})
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level:<8}</level> | <cyan>{extra[request_id]}</cyan> | {message}",
        enqueue=True,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        log_path,
        level=settings.log_level.upper(),
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression="zip",
        enqueue=True,
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    intercept = InterceptHandler()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "multipart"):
        standard_logger = standard_logging.getLogger(name)
        standard_logger.handlers = [intercept]
        standard_logger.propagate = False
