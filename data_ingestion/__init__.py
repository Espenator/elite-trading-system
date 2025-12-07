"""
Data Ingestion Package
======================

All data sources for the Elite Trading System:
- Unusual Whales (Options Flow)
- YFinance (Price Data)
- Finviz Elite (Stock Universe)

Author: Elite Trading Team
Date: December 5, 2025
"""

from .unusual_whales_client import UnusualWhalesClient
from .yfinance_client import YFinanceClient
from .finviz_client import FinvizClient

__all__ = [
    'UnusualWhalesClient',
    'YFinanceClient',
    'FinvizClient'
]

