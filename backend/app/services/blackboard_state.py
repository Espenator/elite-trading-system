"""BlackboardState service: working memory per symbol for perception → council.

Perception events write facts; council/hypothesis reads facts. Exposed via GET /api/v1/blackboard/{symbol}.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

# In-memory store: symbol -> { "facts": {...}, "updated_at": ts }
_store: Dict[str, Dict[str, Any]] = {}
_ttl_sec = 3600 * 24  # 24h


def write_facts(symbol: str, facts: Dict[str, Any], merge: bool = True) -> None:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return
    now = time.time()
    if symbol not in _store:
        _store[symbol] = {"facts": {}, "updated_at": now}
    if merge:
        _store[symbol]["facts"].update(facts)
    else:
        _store[symbol]["facts"] = dict(facts)
    _store[symbol]["updated_at"] = now


def read(symbol: str) -> Optional[Dict[str, Any]]:
    symbol = (symbol or "").strip().upper()
    if not symbol:
        return None
    rec = _store.get(symbol)
    if not rec:
        return None
    if time.time() - rec["updated_at"] > _ttl_sec:
        _store.pop(symbol, None)
        return None
    return {
        "symbol": symbol,
        "facts": dict(rec["facts"]),
        "updated_at": rec["updated_at"],
    }


def get_all_symbols() -> list:
    now = time.time()
    return [
        s for s, rec in _store.items()
        if now - rec["updated_at"] <= _ttl_sec
    ]
