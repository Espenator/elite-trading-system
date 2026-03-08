"""Ingestion layer — event-first adapters for all external data sources.

Each source is wrapped in a BaseSourceAdapter that normalises raw data into
SourceEvent objects, publishes them onto the MessageBus, and persists
checkpoints so that restarts resume where they left off.
"""

from app.services.ingestion.models import SourceEvent, SourceKind  # noqa: F401
from app.services.ingestion.base import BaseSourceAdapter  # noqa: F401
from app.services.ingestion.registry import AdapterRegistry, get_adapter_registry  # noqa: F401
