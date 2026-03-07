"""Feature Aggregator — produce clean, stable feature vectors.

Combines OHLCV data, technical indicators, volume metrics, regime snapshot,
flow features, and intermarket/cycle data into a unified FeatureVector
used by all 13 council agents, XGBoost training, LLM hypothesis prompts,
and critic postmortems.

Usage:
    from app.features.feature_aggregator import aggregate
    fv = await aggregate("AAPL", datetime.now(), "1d")
"""
import hashlib
import json
import logging
import math
from collections import deque
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
    intermarket_features: Dict[str, float] = field(default_factory=dict)
    cycle_features: Dict[str, float] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def _all_features(self) -> Dict[str, Any]:
        """Merge all feature dicts into one."""
        merged = {}
        merged.update(self.price_features)
        merged.update(self.volume_features)
        merged.update(self.volatility_features)
        merged.update(self.regime_features)
        merged.update(self.flow_features)
        merged.update(self.indicator_features)
        merged.update(self.intermarket_features)
        merged.update(self.cycle_features)
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "timeframe": self.timeframe,
            "features": merged,
            "feature_hash": self.hash,
            "feature_count": len(merged),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return self._all_features()

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
        all_features.update(self.intermarket_features)
        all_features.update(self.cycle_features)
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
            sum(volumes[-5:]) / max(len(volumes[-5:]), 1)
            / max(sum(volumes[-20:]) / max(len(volumes[-20:]), 1), 1)
        ) if len(volumes) >= 5 else 1.0,
    }


def _compute_volatility_features(ohlcv_rows: list) -> Dict[str, float]:
    """Compute volatility and ATR-like metrics."""
    if len(ohlcv_rows) < 2:
        return {}
    true_ranges = []
    for i in range(1, len(ohlcv_rows)):
        h = _safe_float(ohlcv_rows[i].get("high"))
        l = _safe_float(ohlcv_rows[i].get("low"))
        prev_c = _safe_float(ohlcv_rows[i - 1].get("close"))
        if h > 0 and l > 0 and prev_c > 0:
            tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
            true_ranges.append(tr)
    if not true_ranges:
        return {}

    atr_14 = sum(true_ranges[-14:]) / max(len(true_ranges[-14:]), 1)
    last_close = _safe_float(ohlcv_rows[-1].get("close"))
    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    returns = [
        (closes[i] / closes[i - 1] - 1)
        for i in range(1, len(closes))
        if closes[i - 1] > 0
    ]
    vol_20d = 0.0
    if len(returns) >= 20:
        mean_ret = sum(returns[-20:]) / 20
        var = sum((r - mean_ret) ** 2 for r in returns[-20:]) / 20
        vol_20d = var ** 0.5

    # Standard deviation of closes for Bollinger Band calculation
    std_20 = 0.0
    if len(closes) >= 20:
        mean_c = sum(closes[-20:]) / 20
        std_20 = (sum((c - mean_c) ** 2 for c in closes[-20:]) / 20) ** 0.5

    return {
        "atr_14": atr_14,
        "atr_pct": atr_14 / max(last_close, 0.01),
        "volatility_20d": vol_20d,
        "volatility_annualized": vol_20d * (252 ** 0.5) if vol_20d > 0 else 0.0,
        "daily_std_dev": std_20,
    }


def _compute_extended_indicators(ohlcv_rows: list) -> Dict[str, float]:
    """Compute extended indicators (EMAs, RSI, MACD) from OHLCV rows."""
    if not ohlcv_rows:
        return {}
    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    if len(closes) < 5:
        return {}

    features: Dict[str, float] = {}

    # Exponential Moving Averages
    for period in (5, 10, 20, 50):
        if len(closes) >= period:
            multiplier = 2 / (period + 1)
            ema = sum(closes[:period]) / period
            for price in closes[period:]:
                ema = (price - ema) * multiplier + ema
            features[f"ema_{period}"] = ema

    # Simple RSI (14-period)
    if len(closes) >= 15:
        gains, losses = [], []
        for i in range(1, len(closes)):
            delta = closes[i] - closes[i - 1]
            gains.append(max(delta, 0))
            losses.append(max(-delta, 0))
        period = 14
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss > 0:
            rs = avg_gain / avg_loss
            features["rsi_14"] = 100 - (100 / (1 + rs))
        else:
            features["rsi_14"] = 100.0

    # MACD (12, 26, 9)
    if len(closes) >= 26:
        ema12 = sum(closes[:12]) / 12
        for p in closes[12:]:
            ema12 = (p - ema12) * (2 / 13) + ema12
        ema26 = sum(closes[:26]) / 26
        for p in closes[26:]:
            ema26 = (p - ema26) * (2 / 27) + ema26
        features["macd"] = ema12 - ema26

    return features


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
        row = conn.execute(
            """SELECT call_volume, put_volume, net_premium, pcr_volume, total_premium
               FROM options_flow
               WHERE symbol = ?
               ORDER BY date DESC LIMIT 1""",
            [symbol.upper()],
        ).fetchone()
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
    """Get latest technical indicator values from DuckDB.

    Expanded to include all keys needed by 13 council agents:
    rsi, bbv, ema_trend, strategy, relative_strength, cycle_timing.
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()

        # Check which columns exist in the table
        try:
            cols_df = conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'technical_indicators'"
            ).fetchall()
            available_cols = {r[0] for r in cols_df} if cols_df else set()
        except Exception:
            available_cols = set()

        # Core indicators (always expected)
        core_cols = [
            "rsi_14", "macd", "macd_signal", "macd_hist",
            "sma_20", "sma_50", "sma_200",
            "ema_9", "ema_21", "atr_14", "atr_21",
            "bb_upper", "bb_lower", "adx_14",
        ]

        # Extended indicators for new agents
        extended_cols = [
            "ema_5", "ema_10", "ema_20",
            "bb_middle", "std_20",
            "rsi_14_prev",
            "relative_strength_spy",
            "rs_rank_percentile",
        ]

        # Build query with available columns only
        query_cols = []
        for col in core_cols + extended_cols:
            if not available_cols or col in available_cols:
                query_cols.append(col)

        if not query_cols:
            return {}

        col_str = ", ".join(query_cols)
        row = conn.execute(
            f"SELECT {col_str} FROM technical_indicators "
            f"WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [symbol.upper()],
        ).fetchone()

        if row:
            result = {}
            for i, col in enumerate(query_cols):
                val = row[i]
                if val is not None:
                    result[f"ind_{col}"] = _safe_float(val)
            return result
    except Exception:
        pass
    return {}


def _get_intermarket_features() -> Dict[str, float]:
    """Get intermarket correlation data (SPY, VIX, DXY, TLT, GLD)."""
    benchmarks = {
        "SPY": "intermarket_spy",
        "VIX": "intermarket_vix",
        "DXY": "intermarket_dxy",
        "TLT": "intermarket_tlt",
        "GLD": "intermarket_gld",
    }
    features = {}
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        for ticker, key in benchmarks.items():
            row = conn.execute(
                "SELECT close FROM daily_ohlcv WHERE symbol = ? "
                "ORDER BY date DESC LIMIT 2",
                [ticker],
            ).fetchall()
            if row and len(row) >= 2:
                last = _safe_float(row[0][0])
                prev = _safe_float(row[1][0])
                if prev > 0:
                    features[f"{key}_return"] = (last / prev) - 1
                    features[f"{key}_price"] = last
    except Exception:
        pass
    return features


def _get_cycle_features(ohlcv_rows: list) -> Dict[str, float]:
    """Compute basic cycle/seasonality features."""
    if not ohlcv_rows:
        return {}

    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    if len(closes) < 20:
        return {}

    # Simple cycle detection: count bars since last local minimum
    bars_since_low = 0
    min_val = closes[-1]
    for i in range(len(closes) - 1, max(len(closes) - 40, 0), -1):
        if closes[i] < min_val:
            min_val = closes[i]
            bars_since_low = len(closes) - 1 - i
            break

    # Price position in recent range
    high_40 = max(closes[-40:]) if len(closes) >= 40 else max(closes)
    low_40 = min(closes[-40:]) if len(closes) >= 40 else min(closes)
    range_40 = high_40 - low_40

    cycle_position = 0.5
    if range_40 > 0:
        cycle_position = (closes[-1] - low_40) / range_40

    # Day of week (0=Mon..4=Fri) — useful for intraday seasonality
    try:
        last_date = ohlcv_rows[-1].get("date")
        if last_date:
            from datetime import datetime as dt
            if isinstance(last_date, str):
                d = dt.fromisoformat(last_date.replace("Z", "+00:00"))
            else:
                d = last_date
            day_of_week = d.weekday()
        else:
            day_of_week = -1
    except Exception:
        day_of_week = -1

    return {
        "cycle_bars_since_low": bars_since_low,
        "cycle_position": round(cycle_position, 4),
        "cycle_range_40d": round(range_40, 4),
        "cycle_day_of_week": day_of_week,
    }


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
        FeatureVector with all available features for 13 council agents
    """
    if ts is None:
        ts = datetime.now(timezone.utc)

    # Get OHLCV data from DuckDB
    ohlcv_rows = []
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()
        df = conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM daily_ohlcv
               WHERE symbol = ?
               ORDER BY date DESC
               LIMIT 60""",
            [symbol.upper()],
        ).fetchdf()
        if not df.empty:
            ohlcv_rows = df.sort_values("date").to_dict("records")
    except Exception as e:
        logger.warning("Failed to fetch OHLCV for %s: %s", symbol, e)

    # Compute features
    indicator_features = _get_indicator_features(symbol)
    # Fill gaps with computed indicators from OHLCV (EMA 5/10/20, prev RSI, etc.)
    extended = _compute_extended_indicators(ohlcv_rows)
    for k, v in extended.items():
        if k not in indicator_features:
            indicator_features[k] = v

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
        intermarket_features=_get_intermarket_features(),
        cycle_features=_get_cycle_features(ohlcv_rows),
    )

    # Persist to feature store if requested
    if persist:
        try:
            from app.data.feature_store import feature_store
            feature_store.store_features(
                symbol, ts, timeframe, fv.to_dict()["features"]
            )
        except Exception as e:
            logger.warning("Failed to persist features for %s: %s", symbol, e)

    logger.debug(
        "Aggregated %d features for %s", fv.to_dict()["feature_count"], symbol
    )
    return fv
