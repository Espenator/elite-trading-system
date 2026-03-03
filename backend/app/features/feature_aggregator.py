"""Feature Aggregator — produce clean, stable feature vectors.

Combines OHLCV data, technical indicators, volume metrics, regime snapshot,
and optional flow features into a unified FeatureVector used by:
- XGBoost training
- LLM hypothesis prompts
- Critic postmortems
- Council agent evaluations

Usage:
    from app.features.feature_aggregator import aggregate
    fv = await aggregate("AAPL", datetime.now(), "1d")
"""
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Typed feature vector with stable hash."""
    symbol: str
    timestamp: str
    timeframe: str
    price_features: Dict[str, float] = field(default_factory=dict)
    volume_features: Dict[str, float] = field(default_factory=dict)
    volatility_features: Dict[str, float] = field(default_factory=dict)
    regime_features: Dict[str, Any] = field(default_factory=dict)
    flow_features: Dict[str, float] = field(default_factory=dict)
    indicator_features: Dict[str, float] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Flatten all features into a single dict."""
        merged = {}
        merged.update(self.price_features)
        merged.update(self.volume_features)
        merged.update(self.volatility_features)
        merged.update(self.regime_features)
        merged.update(self.flow_features)
        merged.update(self.indicator_features)
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "timeframe": self.timeframe,
            "features": merged,
            "feature_hash": self.hash,
            "feature_count": len(merged),
        }

    @property
    def hash(self) -> str:
        """Compute stable hash of all features."""
        all_features = {}
        all_features.update(self.price_features)
        all_features.update(self.volume_features)
        all_features.update(self.volatility_features)
        all_features.update(self.regime_features)
        all_features.update(self.flow_features)
        all_features.update(self.indicator_features)
        canonical = json.dumps(all_features, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _safe_float(val, default=0.0) -> float:
    """Safely convert to float."""
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def _compute_price_features(ohlcv_rows: list) -> Dict[str, float]:
    """Compute price and return statistics from OHLCV data."""
    if not ohlcv_rows:
        return {}

    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    if len(closes) < 2:
        return {"last_close": closes[0] if closes else 0.0}

    last = closes[-1]
    features = {
        "last_close": last,
        "return_1d": (closes[-1] / closes[-2] - 1) if len(closes) >= 2 else 0.0,
        "return_5d": (closes[-1] / closes[-6] - 1) if len(closes) >= 6 else 0.0,
        "return_20d": (closes[-1] / closes[-21] - 1) if len(closes) >= 21 else 0.0,
        "high_20d": max(closes[-20:]) if len(closes) >= 20 else max(closes),
        "low_20d": min(closes[-20:]) if len(closes) >= 20 else min(closes),
    }
    # Distance from 20d high/low
    if features["high_20d"] > 0:
        features["pct_from_20d_high"] = last / features["high_20d"] - 1
    if features["low_20d"] > 0:
        features["pct_from_20d_low"] = last / features["low_20d"] - 1

    return features


def _compute_volume_features(ohlcv_rows: list) -> Dict[str, float]:
    """Compute volume surge and relative volume metrics."""
    if not ohlcv_rows:
        return {}

    volumes = [_safe_float(r.get("volume")) for r in ohlcv_rows if r.get("volume")]
    if not volumes:
        return {}

    last_vol = volumes[-1]
    avg_20 = sum(volumes[-20:]) / max(len(volumes[-20:]), 1)

    return {
        "last_volume": last_vol,
        "volume_sma_20": avg_20,
        "volume_surge_ratio": last_vol / max(avg_20, 1),
        "volume_trend_5d": (
            sum(volumes[-5:]) / max(len(volumes[-5:]), 1) /
            max(sum(volumes[-20:]) / max(len(volumes[-20:]), 1), 1)
        ) if len(volumes) >= 5 else 1.0,
    }


def _compute_volatility_features(ohlcv_rows: list) -> Dict[str, float]:
    """Compute volatility and ATR-like metrics."""
    if len(ohlcv_rows) < 2:
        return {}

    # True Range calculation
    true_ranges = []
    for i in range(1, len(ohlcv_rows)):
        h = _safe_float(ohlcv_rows[i].get("high"))
        l = _safe_float(ohlcv_rows[i].get("low"))
        prev_c = _safe_float(ohlcv_rows[i-1].get("close"))
        if h > 0 and l > 0 and prev_c > 0:
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            true_ranges.append(tr)

    if not true_ranges:
        return {}

    atr_14 = sum(true_ranges[-14:]) / max(len(true_ranges[-14:]), 1)
    last_close = _safe_float(ohlcv_rows[-1].get("close"))

    # Daily returns for volatility
    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    returns = [(closes[i] / closes[i-1] - 1) for i in range(1, len(closes)) if closes[i-1] > 0]

    vol_20d = 0.0
    if len(returns) >= 20:
        mean_ret = sum(returns[-20:]) / 20
        var = sum((r - mean_ret) ** 2 for r in returns[-20:]) / 20
        vol_20d = var ** 0.5

    return {
        "atr_14": atr_14,
        "atr_pct": atr_14 / max(last_close, 0.01),
        "volatility_20d": vol_20d,
        "volatility_annualized": vol_20d * (252 ** 0.5) if vol_20d > 0 else 0.0,
    }


def _get_regime_snapshot() -> Dict[str, Any]:
    """Get current market regime from regime service if available."""
    try:
        from app.services.regime_service import get_current_regime
        regime = get_current_regime()
        if regime:
            return {
                "regime": str(regime.get("regime", "unknown")),
                "regime_confidence": _safe_float(regime.get("confidence", 0.5)),
            }
    except (ImportError, Exception):
        pass
    return {"regime": "unknown", "regime_confidence": 0.0}


def _get_flow_features(symbol: str) -> Dict[str, float]:
    """Get options flow features if available."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        row = conn.execute("""
            SELECT call_volume, put_volume, net_premium, pcr_volume, total_premium
            FROM options_flow
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """, [symbol.upper()]).fetchone()
        if row:
            return {
                "flow_call_volume": _safe_float(row[0]),
                "flow_put_volume": _safe_float(row[1]),
                "flow_net_premium": _safe_float(row[2]),
                "flow_pcr": _safe_float(row[3]),
                "flow_total_premium": _safe_float(row[4]),
            }
    except Exception:
        pass
    return {}


def _get_indicator_features(symbol: str) -> Dict[str, float]:
    """Get latest technical indicator values from DuckDB."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        row = conn.execute("""
            SELECT rsi_14, macd, macd_signal, macd_hist, sma_20, sma_50, sma_200,
                   ema_9, ema_21, atr_14, atr_21, bb_upper, bb_lower, adx_14
            FROM technical_indicators
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """, [symbol.upper()]).fetchone()
        if row:
            names = ["rsi_14", "macd", "macd_signal", "macd_hist", "sma_20", "sma_50",
                     "sma_200", "ema_9", "ema_21", "atr_14", "atr_21", "bb_upper",
                     "bb_lower", "adx_14"]
            return {f"ind_{n}": _safe_float(v) for n, v in zip(names, row) if v is not None}
    except Exception:
        pass
    return {}


async def aggregate(
    symbol: str,
    ts: Optional[datetime] = None,
    timeframe: str = "1d",
    persist: bool = False,
) -> FeatureVector:
    """Aggregate all features for a symbol into a FeatureVector.

    Args:
        symbol: Ticker symbol
        ts: Timestamp (defaults to now)
        timeframe: Timeframe for features
        persist: If True, store to DuckDB feature store

    Returns:
        FeatureVector with all available features
    """
    if ts is None:
        ts = datetime.now(timezone.utc)

    # Get OHLCV data from DuckDB
    ohlcv_rows = []
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        df = conn.execute("""
            SELECT date, open, high, low, close, volume
            FROM daily_ohlcv
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 60
        """, [symbol.upper()]).fetchdf()
        if not df.empty:
            # Convert to list of dicts, sorted oldest first
            ohlcv_rows = df.sort_values("date").to_dict("records")
    except Exception as e:
        logger.warning("Failed to fetch OHLCV for %s: %s", symbol, e)

    # Compute features
    fv = FeatureVector(
        symbol=symbol.upper(),
        timestamp=ts.isoformat() if isinstance(ts, datetime) else str(ts),
        timeframe=timeframe,
        price_features=_compute_price_features(ohlcv_rows),
        volume_features=_compute_volume_features(ohlcv_rows),
        volatility_features=_compute_volatility_features(ohlcv_rows),
        regime_features=_get_regime_snapshot(),
        flow_features=_get_flow_features(symbol),
        indicator_features=_get_indicator_features(symbol),
    )

    # Persist to feature store if requested
    if persist:
        try:
            from app.data.feature_store import feature_store
            feature_store.store_features(symbol, ts, timeframe, fv.to_dict()["features"])
        except Exception as e:
            logger.warning("Failed to persist features for %s: %s", symbol, e)

    logger.debug("Aggregated %d features for %s", fv.to_dict()["feature_count"], symbol)
    return fv
