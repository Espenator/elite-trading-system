"""Structured JSON logging configuration for production.

In production (ENVIRONMENT != "development"), logs are JSON-formatted for
consumption by log aggregators (ELK, Loki, CloudWatch).
In development, logs use human-readable format.

Adds correlation_id to every log record via middleware + context var.
Automatically redacts sensitive data (API keys, tokens, secrets) from logs.
"""
import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar

from app.core.config import settings

# Context variable for request correlation ID
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

# Patterns to redact from log messages (case-insensitive)
REDACT_PATTERNS = [
    (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(secret[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(token["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(bearer\s+)([a-zA-Z0-9_\-\.]+)', re.IGNORECASE), r'\1[REDACTED]'),
    (re.compile(r'(authorization["\']?\s*[:=]\s*["\']?)([^"\'}\s,]+)', re.IGNORECASE), r'\1[REDACTED]'),
]


def redact_sensitive_data(message: str) -> str:
    """Redact sensitive information from log message."""
    for pattern, replacement in REDACT_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


class JSONFormatter(logging.Formatter):
    """JSON log formatter for production with automatic secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        # Redact sensitive data from message
        original_msg = record.getMessage()
        redacted_msg = redact_sensitive_data(original_msg)

        log_dict = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "msg": redacted_msg,
            "correlation_id": correlation_id.get("-"),
        }
        if record.exc_info and record.exc_info[0]:
            exc_text = self.formatException(record.exc_info)
            log_dict["exception"] = redact_sensitive_data(exc_text)
        if hasattr(record, "status_code"):
            log_dict["status_code"] = record.status_code
        return json.dumps(log_dict, default=str)


class DevFormatter(logging.Formatter):
    """Human-readable log formatter for development with automatic secret redaction."""

    def format(self, record: logging.LogRecord) -> str:
        cid = correlation_id.get("-")
        cid_str = f" [{cid[:8]}]" if cid != "-" else ""
        record.cid = cid_str

        # Redact sensitive data from message
        original_msg = record.getMessage()
        record.msg = redact_sensitive_data(original_msg)

        formatted = super().format(record)
        return redact_sensitive_data(formatted)


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
