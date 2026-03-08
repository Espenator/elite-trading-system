"""Scanning sub-package — signal generation, market scanning, pattern discovery.

Re-exports from the flat services/ directory for organized imports.
Existing imports still work.
"""
from app.services import signal_engine  # noqa: F401
from app.services import turbo_scanner  # noqa: F401
from app.services import market_wide_sweep  # noqa: F401
from app.services import correlation_radar  # noqa: F401
from app.services import pattern_library  # noqa: F401
from app.services import expected_move_service  # noqa: F401
from app.services import news_aggregator  # noqa: F401
from app.services import geopolitical_radar  # noqa: F401
from app.services import autonomous_scout  # noqa: F401
from app.services import scouts  # noqa: F401  — E2: 12 dedicated scout agents
