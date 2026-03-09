"""
Ingestion Adapters

All data source adapters for the ingestion framework.
"""

from app.services.ingestion.adapters.finviz_adapter import FinvizAdapter
from app.services.ingestion.adapters.fred_adapter import FREDAdapter
from app.services.ingestion.adapters.unusual_whales_adapter import UnusualWhalesAdapter
from app.services.ingestion.adapters.sec_edgar_adapter import SECEdgarAdapter
from app.services.ingestion.adapters.openclaw_adapter import OpenClawAdapter
from app.services.ingestion.adapters.alpaca_stream_adapter import AlpacaStreamAdapter

__all__ = [
    "FinvizAdapter",
    "FREDAdapter",
    "UnusualWhalesAdapter",
    "SECEdgarAdapter",
    "OpenClawAdapter",
    "AlpacaStreamAdapter",
]
