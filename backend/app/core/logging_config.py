"""Structured JSON logging configuration for production.

In production (ENVIRONMENT != "development"), logs are JSON-formatted for
consumption by log aggregators (ELK, Loki, CloudWatch).
In development, logs use human-readable format.

Adds correlation_id to every log record via middleware + context var.
"""
import json
import logging
import sys
import uuid
from contextvars import ContextVar

from app.core.config import settings

# Context variable for request correlation ID
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": correlation_id.get("-"),
        }
        if record.exc_info and record.exc_info[0]:
            log_dict["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "status_code"):
            log_dict["status_code"] = record.status_code
        return json.dumps(log_dict, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable log formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        cid = correlation_id.get("-")
        cid_str = f" [{cid[:8]}]" if cid != "-" else ""
        record.cid = cid_str
        return super().format(record)


def setup_logging() -> None:
    """Configure root logger based on environment."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    is_prod = settings.ENVIRONMENT.lower() not in ("development", "dev", "local")

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if is_prod:
        handler.setFormatter(JSONFormatter(datefmt="%Y-%m-%dT%H:%M:%S"))
    else:
        handler.setFormatter(DevFormatter(
            fmt="%(asctime)s%(cid)s %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        ))

    root.addHandler(handler)

    # Reduce noise from chatty libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def generate_correlation_id() -> str:
    """Generate a short correlation ID for request tracing."""
    return uuid.uuid4().hex[:12]
