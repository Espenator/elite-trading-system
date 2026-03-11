"""Structured JSON logging configuration for production.

In production (ENVIRONMENT != "development"), logs are JSON-formatted for
consumption by log aggregators (ELK, Loki, CloudWatch).
In development, logs use human-readable format.

Adds correlation_id to every log record via middleware + context var.
Includes an in-memory ring buffer for the /api/v1/logs endpoint.
"""
import json
import logging
import sys
import uuid
from collections import deque
from contextvars import ContextVar
from datetime import datetime, timezone
from threading import Lock

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

    # Add ring buffer handler for /api/v1/logs endpoint
    global _ring_handler
    _ring_handler = RingBufferHandler()
    _ring_handler.setLevel(logging.INFO)
    root.addHandler(_ring_handler)

    # Reduce noise from chatty libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RingBufferHandler(logging.Handler):
    """In-memory ring buffer that stores the last N log records for the /api/v1/logs endpoint."""

    _MAX = 500

    def __init__(self, capacity: int = _MAX):
        super().__init__()
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Derive source/type from logger name
            name = record.name or ""
            source = "system"
            log_type = "system"
            if "signal" in name:
                source, log_type = "signals", "signal"
            elif "council" in name:
                source, log_type = "agents", "council"
            elif "risk" in name:
                source, log_type = "agents", "risk"
            elif "agent" in name or "scout" in name or "swarm" in name:
                source, log_type = "agents", "agent"
            elif "data" in name or "alpaca" in name or "finviz" in name:
                source, log_type = "data-sources", "data"
            elif "sentiment" in name or "news" in name:
                source, log_type = "sentiment", "sentiment"
            elif "ml" in name or "brain" in name or "train" in name:
                source, log_type = "ml", "ml"
            elif "order" in name or "execution" in name:
                source, log_type = "execution", "trade"

            entry = {
                "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname.lower(),
                "message": record.getMessage(),
                "source": source,
                "agent": name.rsplit(".", 1)[-1] if "." in name else name,
                "type": log_type,
                "ticker": None,
                "confidence": None,
                "pnlImpact": "—",
            }
            with self._lock:
                self._buffer.append(entry)
        except Exception:
            pass

    def get_recent(self, limit: int = 100) -> list:
        with self._lock:
            items = list(self._buffer)
        return items[-limit:][::-1]  # newest first


# Module-level singleton
_ring_handler: RingBufferHandler | None = None


def get_ring_buffer() -> RingBufferHandler:
    """Return the singleton ring buffer handler (created in setup_logging)."""
    global _ring_handler
    if _ring_handler is None:
        _ring_handler = RingBufferHandler()
    return _ring_handler


def generate_correlation_id() -> str:
    """Generate a short correlation ID for request tracing."""
    return uuid.uuid4().hex[:12]
