"""
Structured Logging Configuration

Provides JSON-formatted logging with request correlation IDs,
log levels per environment, and consistent structure across the application.
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra"):
            log_entry.update(record.extra)

        return json.dumps(log_entry, default=str)


class PlainTextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        request_id = getattr(record, "request_id", "-")[:8]
        return f"{timestamp} [{record.levelname:<8}] [{request_id}] {record.name}: {record.getMessage()}"


def setup_logging(
    level: str = "INFO",
    format_type: str = "text",
    request_id: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "json" for production, "text" for development
        request_id: Optional request correlation ID
    """
    formatter = JSONFormatter() if format_type == "json" else PlainTextFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_request_logger(name: str, request_id: Optional[str] = None) -> logging.LoggerAdapter:
    """
    Get a logger adapter that injects request_id into all log records.

    Usage:
        logger = get_request_logger(__name__, request_id)
        logger.info("Processing request", extra={"user_id": user.id})
    """
    logger = logging.getLogger(name)
    extra = {"request_id": request_id or "no-request"} if request_id else {}
    return logging.LoggerAdapter(logger, extra)


def process(record: logging.LogRecord) -> logging.LogRecord:
    """Process log record to add extra fields."""
    if hasattr(record, "request_id"):
        pass  # Already set
    return record
