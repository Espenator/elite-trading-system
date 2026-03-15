"""GPU Channel 5 — Streaming GPU Bar Aggregation.

Batches incoming Alpaca WebSocket bars into GPU tensors for rolling indicator
computation across 500+ symbols simultaneously. Pattern: accumulate bars in a
deque, flush to GPU every 100ms for VWAP/TWAP/rolling-vol computation.

Falls back to NumPy on CPU when CuPy is unavailable.

Usage:
    from app.modules.ml_engine.gpu_bar_aggregator import get_bar_aggregator
    agg = get_bar_aggregator()
    agg.ingest(bar_data)  # called per bar
    indicators = agg.flush()  # called every 100ms
"""
import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# GPU Channel 5: CuPy for GPU tensor operations
try:
    import cupy as cp
    GPU_BARS = True
    logger.info("GPU Bar Aggregator: CuPy ENABLED for streaming indicator compute")
except ImportError:
    cp = np  # type: ignore[assignment]
    GPU_BARS = False

# Rolling window sizes
VWAP_WINDOW = 20
VOL_WINDOW = 20
FLUSH_INTERVAL_MS = 100  # Flush to GPU every 100ms
MAX_BARS_PER_SYMBOL = 100  # Keep last 100 bars in memory


class GPUBarAggregator:
    """Streaming GPU-accelerated bar aggregation and indicator computation."""

    def __init__(self):
        self._bars: Dict[str, deque] = defaultdict(lambda: deque(maxlen=MAX_BARS_PER_SYMBOL))
        self._last_flush = 0.0
        self._flush_count = 0

    def ingest(self, bar: Dict[str, Any]) -> None:
        """Ingest a single bar into the aggregation buffer."""
        symbol = bar.get("S") or bar.get("symbol") or bar.get("ticker", "")
        if not symbol:
            return
        self._bars[symbol].append({
            "close": float(bar.get("c") or bar.get("close", 0)),
            "high": float(bar.get("h") or bar.get("high", 0)),
            "low": float(bar.get("l") or bar.get("low", 0)),
            "open": float(bar.get("o") or bar.get("open", 0)),
            "volume": float(bar.get("v") or bar.get("volume", 0)),
            "vwap": float(bar.get("vw") or bar.get("vwap", 0)),
            "ts": time.time(),
        })

    def ingest_batch(self, bars: List[Dict[str, Any]]) -> None:
        """Ingest multiple bars at once."""
        for bar in bars:
            self.ingest(bar)

    def flush(self) -> Dict[str, Dict[str, float]]:
        """Flush accumulated bars to GPU and compute rolling indicators.

        Returns dict of symbol -> {vwap, twap, rolling_vol, volume_surge, bar_count}.
        """
        now = time.monotonic() * 1000
        if now - self._last_flush < FLUSH_INTERVAL_MS and self._flush_count > 0:
            return {}

        self._last_flush = now
        self._flush_count += 1
        xp = cp if GPU_BARS else np
        results = {}

        for symbol, bar_deque in self._bars.items():
            if len(bar_deque) < 2:
                continue

            bars_list = list(bar_deque)
            try:
                closes = xp.array([b["close"] for b in bars_list], dtype=xp.float32)
                volumes = xp.array([b["volume"] for b in bars_list], dtype=xp.float32)
                highs = xp.array([b["high"] for b in bars_list], dtype=xp.float32)
                lows = xp.array([b["low"] for b in bars_list], dtype=xp.float32)

                n = len(closes)
                window = min(VWAP_WINDOW, n)

                # VWAP (volume-weighted average price)
                recent_closes = closes[-window:]
                recent_volumes = volumes[-window:]
                total_vol = float(xp.sum(recent_volumes))
                vwap = float(xp.sum(recent_closes * recent_volumes) / total_vol) if total_vol > 0 else float(closes[-1])

                # TWAP (time-weighted average price)
                twap = float(xp.mean(recent_closes))

                # Rolling volatility (annualized)
                if n >= 3:
                    returns = xp.diff(xp.log(closes[-min(VOL_WINDOW + 1, n):]))
                    rolling_vol = float(xp.std(returns)) * (252 ** 0.5) if len(returns) > 1 else 0.0
                else:
                    rolling_vol = 0.0

                # Volume surge ratio
                if n >= VWAP_WINDOW:
                    avg_vol = float(xp.mean(volumes[-VWAP_WINDOW:]))
                    vol_surge = float(volumes[-1] / avg_vol) if avg_vol > 0 else 1.0
                else:
                    vol_surge = 1.0

                # Intraday range
                range_pct = float((highs[-1] - lows[-1]) / closes[-1]) if float(closes[-1]) > 0 else 0.0

                results[symbol] = {
                    "vwap": round(vwap, 4),
                    "twap": round(twap, 4),
                    "rolling_vol": round(rolling_vol, 4),
                    "volume_surge": round(vol_surge, 2),
                    "range_pct": round(range_pct, 4),
                    "bar_count": n,
                    "gpu": GPU_BARS,
                }
            except Exception as e:
                logger.debug("GPU bar aggregation failed for %s: %s", symbol, e)

        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "gpu_enabled": GPU_BARS,
            "symbols_tracked": len(self._bars),
            "total_bars": sum(len(d) for d in self._bars.values()),
            "flush_count": self._flush_count,
        }


# Singleton
_aggregator: Optional[GPUBarAggregator] = None


def get_bar_aggregator() -> GPUBarAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = GPUBarAggregator()
    return _aggregator
