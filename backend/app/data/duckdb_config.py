"""
Shared DuckDB runtime tuning for ESPENMAIN.
"""

import logging
from typing import Optional


def configure_duckdb(conn, logger: Optional[logging.Logger] = None) -> None:
    """
    Apply runtime DuckDB settings for local performance tuning.

    Settings are best-effort so connection creation remains safe if a given
    setting is unsupported in the installed DuckDB version.
    """
    log = logger or logging.getLogger(__name__)
    statements = [
        "SET threads=12",
        # ESPENMAIN 48GB leaves headroom for OS + GPU transfers.
        "SET memory_limit='48GB'",
        "SET temp_directory='/tmp/duckdb_spill'",
        "SET enable_progress_bar=false",
        "SET preserve_insertion_order=false",
        "PRAGMA enable_object_cache=true",
    ]

    for statement in statements:
        try:
            conn.execute(statement)
        except Exception as exc:
            log.warning("DuckDB tuning statement failed (%s): %s", statement, exc)
