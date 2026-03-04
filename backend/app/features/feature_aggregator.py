"""Feature Aggregator — produce clean, stable feature vectors.

Combines OHLCV data, technical indicators, volume metrics, regime snapshot,
flow features, intermarket data, benchmark returns, and multi-timeframe
indicators into a unified FeatureVector used by:
- XGBoost training
- LLM hypothesis prompts
- Critic postmortems
- Council agent evaluations (all 17 agents)

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
    benchmark_features: Dict[str, float] = field(default_factory=dict)
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
        merged.update(self.benchmark_features)
        return merged

    def to_dict(self) -> Dict[str, Any]:
        """Flatten all features into a single dict."""
        merged = self._all_features()
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
        canonical = json.dumps(self._all_features(), sort_keys=True, default=str)
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


def _compute_ema(values: List[float], span: int) -> float:
    """Compute EMA for a given span over a list of values."""
    if not values or span <= 0:
        return 0.0
    k = 2.0 / (span + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _compute_rsi(closes: List[float], period: int = 14) -> float:
    """Compute RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0.0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _compute_extended_indicators(ohlcv_rows: list) -> Dict[str, float]:
    """Compute additional indicators needed by technical agents.

    Fills the gaps for: ema_trend_agent (EMA 5/10/20), rsi_agent (prev RSI).
    These are computed directly from OHLCV when DuckDB indicators are unavailable.
    """
    if len(ohlcv_rows) < 5:
        return {}

    closes = [_safe_float(r.get("close")) for r in ohlcv_rows if r.get("close")]
    if len(closes) < 5:
        return {}

    features: Dict[str, float] = {}

    # EMA 5, 10, 20 for ema_trend_agent
    features["ind_ema_5"] = _compute_ema(closes, 5)
    features["ind_ema_10"] = _compute_ema(closes, 10)
    if len(closes) >= 20:
        features["ind_ema_20"] = _compute_ema(closes, 20)

    # Previous RSI for slope calculation (rsi_agent)
    if len(closes) >= 16:
        features["rsi_14_prev"] = _compute_rsi(closes[:-1], 14)

    # 60-day return for relative_strength_agent
    if len(closes) >= 61:
        features["return_60d"] = closes[-1] / closes[-61] - 1

    return features


def _get_intermarket_features(symbol: str) -> Dict[str, float]:
    """Compute intermarket correlation and VIX features for intermarket_agent.

    Fetches SPY, UVXY, IEF, IWM data from DuckDB to compute rolling correlations,
    and VIX level from regime service or DuckDB.
    """
    features: Dict[str, float] = {}

    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()

        # Get the symbol's recent returns
        sym_df = conn.execute("""
            SELECT close FROM daily_ohlcv
            WHERE symbol = ? ORDER BY date DESC LIMIT 21
        """, [symbol.upper()]).fetchall()
        sym_closes = [_safe_float(r[0]) for r in reversed(sym_df)] if sym_df else []

        if len(sym_closes) >= 6:
            sym_returns = [(sym_closes[i] / sym_closes[i - 1] - 1)
                           for i in range(1, len(sym_closes))]

            # Fetch benchmark returns for correlation
            for bench_sym, key_prefix in [
                ("SPY", "spy"), ("UVXY", "uvxy"), ("IEF", "ief"), ("IWM", "iwm")
            ]:
                bench_df = conn.execute("""
                    SELECT close FROM daily_ohlcv
                    WHERE symbol = ? ORDER BY date DESC LIMIT 21
                """, [bench_sym]).fetchall()
                if bench_df and len(bench_df) >= 6:
                    bench_closes = [_safe_float(r[0]) for r in reversed(bench_df)]
                    bench_returns = [(bench_closes[i] / bench_closes[i - 1] - 1)
                                     for i in range(1, len(bench_closes))]
                    # Compute correlation over matching length
                    n = min(len(sym_returns), len(bench_returns))
                    if n >= 5:
                        sr = sym_returns[-n:]
                        br = bench_returns[-n:]
                        mean_s = sum(sr) / n
                        mean_b = sum(br) / n
                        cov = sum((s - mean_s) * (b - mean_b) for s, b in zip(sr, br)) / n
                        std_s = (sum((s - mean_s) ** 2 for s in sr) / n) ** 0.5
                        std_b = (sum((b - mean_b) ** 2 for b in br) / n) ** 0.5
                        if std_s > 0 and std_b > 0:
                            corr = cov / (std_s * std_b)
                            corr = max(-1.0, min(1.0, corr))
                        else:
                            corr = 0.0

                        if bench_sym == "SPY":
                            features["ticker_spy_correlation"] = corr
                            # Beta = cov(sym, spy) / var(spy)
                            var_spy = sum((b - mean_b) ** 2 for b in br) / n
                            features["beta"] = cov / var_spy if var_spy > 0 else 1.0
                        elif bench_sym == "UVXY":
                            features["spy_uvxy_correlation"] = corr
                        elif bench_sym == "IEF":
                            features["spy_ief_correlation"] = corr
                        elif bench_sym == "IWM":
                            features["spy_iwm_correlation"] = corr

        # VIX level from DuckDB
        vix_row = conn.execute("""
            SELECT close FROM daily_ohlcv
            WHERE symbol IN ('VIX', '^VIX', 'VIXY')
            ORDER BY date DESC LIMIT 2
        """).fetchall()
        if vix_row:
            vix_closes = [_safe_float(r[0]) for r in vix_row]
            features["vix_level"] = vix_closes[0]
            if len(vix_closes) >= 2 and vix_closes[1] > 0:
                features["vix_change_pct"] = (vix_closes[0] / vix_closes[1] - 1) * 100

    except Exception as e:
        logger.debug("Intermarket features unavailable: %s", e)

    # Sector breadth from finviz if available
    try:
        from app.services.screener_service import get_sector_performance
        sectors = get_sector_performance()
        if sectors:
            bullish = sum(1 for s in sectors if _safe_float(s.get("change", 0)) > 0)
            features["sector_bullish_pct"] = (bullish / len(sectors)) * 100
    except Exception:
        pass

    return features


def _get_benchmark_features(symbol: str) -> Dict[str, float]:
    """Compute benchmark return features for relative_strength_agent.

    Gets SPY returns at 5d/20d/60d horizons for excess return calculation.
    """
    features: Dict[str, float] = {}

    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store._get_conn()

        spy_df = conn.execute("""
            SELECT close FROM daily_ohlcv
            WHERE symbol = 'SPY' ORDER BY date DESC LIMIT 61
        """).fetchall()
        if spy_df:
            spy_closes = [_safe_float(r[0]) for r in reversed(spy_df)]
            if len(spy_closes) >= 6:
                features["spy_return_5d"] = spy_closes[-1] / spy_closes[-6] - 1
            if len(spy_closes) >= 21:
                features["spy_return_20d"] = spy_closes[-1] / spy_closes[-21] - 1
            if len(spy_closes) >= 61:
                features["spy_return_60d"] = spy_closes[-1] / spy_closes[-61] - 1

        # Peer percentile: rank this symbol's 20d return vs sector peers
        sym_row = conn.execute("""
            SELECT close FROM daily_ohlcv
            WHERE symbol = ? ORDER BY date DESC LIMIT 21
        """, [symbol.upper()]).fetchall()
        if sym_row and len(sym_row) >= 21:
            sym_closes = [_safe_float(r[0]) for r in reversed(sym_row)]
            sym_ret_20d = sym_closes[-1] / sym_closes[0] - 1

            # Get a representative set of liquid stocks for peer comparison
            peer_df = conn.execute("""
                SELECT symbol, (
                    SELECT close FROM daily_ohlcv d2
                    WHERE d2.symbol = d1.symbol ORDER BY date DESC LIMIT 1
                ) as last_close,
                (
                    SELECT close FROM daily_ohlcv d3
                    WHERE d3.symbol = d1.symbol ORDER BY date ASC
                    LIMIT 1 OFFSET (
                        SELECT MAX(0, COUNT(*) - 21) FROM daily_ohlcv d4
                        WHERE d4.symbol = d1.symbol
                    )
                ) as close_21ago
                FROM (SELECT DISTINCT symbol FROM daily_ohlcv) d1
                LIMIT 50
            """).fetchall()
            if peer_df and len(peer_df) >= 5:
                peer_returns = []
                for row in peer_df:
                    lc = _safe_float(row[1])
                    c21 = _safe_float(row[2])
                    if lc > 0 and c21 > 0:
                        peer_returns.append(lc / c21 - 1)
                if peer_returns:
                    below = sum(1 for r in peer_returns if r < sym_ret_20d)
                    features["peer_percentile_20d"] = below / len(peer_returns)

            # RS line slope (relative strength vs SPY over 20d)
            if "spy_return_20d" in features:
                excess = sym_ret_20d - features["spy_return_20d"]
                features["excess_return_20d"] = excess
                # Approximate RS line slope as daily excess return
                features["rs_line_slope"] = excess / 20

    except Exception as e:
        logger.debug("Benchmark features unavailable: %s", e)

    return features


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
        indicator_features=indicator_features,
        intermarket_features=_get_intermarket_features(symbol),
        benchmark_features=_get_benchmark_features(symbol),
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
