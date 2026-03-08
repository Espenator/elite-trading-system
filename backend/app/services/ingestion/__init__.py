"""
Ingestion Framework

Base classes and utilities for data ingestion.
"""

from app.services.ingestion.base import BaseSourceAdapter
from app.services.ingestion.registry import AdapterRegistry
from app.services.ingestion.scheduler import IngestionScheduler

__all__ = ["BaseSourceAdapter", "AdapterRegistry", "IngestionScheduler"]
