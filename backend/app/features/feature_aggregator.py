"""Feature Aggregator — produce clean, stable feature vectors from real data.

Combines OHLCV data, technical indicators, volume metrics, regime snapshot,
flow features, and intermarket/cycle data into a unified FeatureVector
used by all 35 council agents. All data comes from configured providers
(DuckDB-backed); no mock data. Missing or stale data is surfaced via
data_freshness and provider_health so the council can HOLD instead of
trading on silent zero defaults.

Usage:
    from app.features.feature_aggregator import aggregate
    fv = await aggregate("AAPL", datetime.now(timezone.utc), "1d")
    d = fv.to_dict()  # includes data_quality, data_freshness, provider_health
"""
import asyncio
import hashlib
import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Expected feature keys for data_quality (council agents rely on these)
EXPECTED_FEATURE_KEYS = frozenset({
    "last_close", "return_1d", "return_5d", "return_20d",
    "last_volume", "volume_surge_ratio", "volume_trend_5d",
    "atr_14", "atr_pct", "volatility_20d", "rsi_14",
    "regime", "regime_confidence", "vix_close", "vix_level",
    "intermarket_spy_return", "intermarket_vix_return", "ticker_spy_correlation",
    "spy_uvxy_correlation", "sector_bullish_pct", "beta",
    "cycle_position", "cycle_bars_since_low",
})


def _compute_data_quality(
    merged: Dict[str, Any],
    is_sufficient: bool = True,
    missing_data_reason: str = "",
    provider_health: Optional[Dict[str, Any]] = None,
    data_freshness: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute data_quality dict for observability and agent context.

    When is_sufficient is False, council should treat as HOLD (no trade on stale/missing data).
    """
    present = set(merged.keys())
    missing = list(EXPECTED_FEATURE_KEYS - present)
    total_expected = max(len(EXPECTED_FEATURE_KEYS), 1)
    present_count = len(present)
    quality_score = round(min(1.0, present_count / total_expected), 2)
    out = {
        "total_features_expected": total_expected,
        "features_present": present_count,
        "features_missing": missing[:15],
        "quality_score": quality_score,
        "stale_features": [],
        "is_sufficient": is_sufficient,
        "missing_data_reason": missing_data_reason or "",
    }
    if provider_health:
        out["provider_health"] = provider_health
    if data_freshness:
        out["data_freshness"] = data_freshness
    return out


@dataclass
class FeatureVector:
    """Typed feature vector with stable hash, freshness and provider health."""

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
    data_quality: Optional[Dict[str, Any]] = None
    data_freshness: Optional[Dict[str, Any]] = None
    provider_health: Optional[Dict[str, Any]] = None

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
        """Convert to dictionary; includes data_quality, data_freshness, provider_health when set."""
        out = self._all_features()
        if self.data_quality is not None:
            out["data_quality"] = self.data_quality
        if self.data_freshness is not None:
            out["data_freshness"] = self.data_freshness
        if self.provider_health is not None:
            out["provider_health"] = self.provider_health
        return out

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
    """Classify market regime from VIX level + SPY trend.

    Regime ladder (VIX-driven, trend-confirmed):
        VIX < 15  + SPY uptrend   → bullish        (conf 0.8)
        VIX < 15  + SPY flat/down → trending_up     (conf 0.6)
        VIX 15-20                 → normal          (conf 0.5)
        VIX 20-30 + SPY downtrend → volatile        (conf 0.7)
        VIX 20-30 + SPY flat/up   → choppy          (conf 0.5)
        VIX > 30                  → bearish          (conf 0.8)
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()

        # VIX level
        vix_row = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = 'VIX' "
            "ORDER BY date DESC LIMIT 1"
        ).fetchone()
        vix = _safe_float(vix_row[0]) if vix_row else 0

        # SPY 20-day return for trend
        spy_rows = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = 'SPY' "
            "ORDER BY date DESC LIMIT 21"
        ).fetchall()
        spy_return_20d = 0.0
        if len(spy_rows) >= 21:
            spy_return_20d = (spy_rows[0][0] - spy_rows[20][0]) / spy_rows[20][0] if spy_rows[20][0] else 0

        uptrend = spy_return_20d > 0.01
        downtrend = spy_return_20d < -0.01

        if vix <= 0:
            return {"regime": "unknown", "regime_confidence": 0.0, "vix_close": 0}

        if vix > 30:
            regime, conf = "bearish", 0.8
        elif vix > 20:
            if downtrend:
                regime, conf = "volatile", 0.7
            else:
                regime, conf = "choppy", 0.5
        elif vix > 15:
            regime, conf = "normal", 0.5
        else:
            if uptrend:
                regime, conf = "bullish", 0.8
            else:
                regime, conf = "trending_up", 0.6

        return {
            "regime": regime,
            "regime_confidence": conf,
            "vix_close": vix,
            "spy_return_20d": round(spy_return_20d, 4),
        }
    except Exception:
        pass
    return {"regime": "unknown", "regime_confidence": 0.0}


def _get_flow_features(symbol: str) -> Dict[str, float]:
    """Get options flow features if available."""
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
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
        conn = duckdb_store.get_thread_cursor()

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
    except Exception as e:
        logger.error("Indicator feature aggregation failed: %s", e)
    return {"_aggregation_failed": True, "_error": "indicator_features"}


def _rolling_correlation(xs: List[float], ys: List[float], window: int = 20) -> float:
    """Compute Pearson correlation over last `window` observations."""
    n = min(len(xs), len(ys), window)
    if n < 5:
        return 0.0
    x = xs[-n:]
    y = ys[-n:]
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
    sy = sum((yi - my) ** 2 for yi in y) ** 0.5
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return cov / (sx * sy)


def _get_intermarket_features(symbol: str = "") -> Dict[str, float]:
    """Get intermarket returns, correlations, and beta.

    Returns daily returns for SPY/VIX/DXY/TLT/GLD, plus rolling 20-day
    correlations for SPY-UVXY, SPY-IEF, SPY-IWM, and ticker-vs-SPY beta.
    """
    benchmarks = {
        "SPY": "intermarket_spy",
        "VIX": "intermarket_vix",
        "DXY": "intermarket_dxy",
        "TLT": "intermarket_tlt",
        "GLD": "intermarket_gld",
    }
    # Pairs whose rolling correlation the intermarket_agent needs
    corr_pairs = {
        ("SPY", "UVXY"): "spy_uvxy_correlation",
        ("SPY", "IEF"): "spy_ief_correlation",
        ("SPY", "IWM"): "spy_iwm_correlation",
    }
    features: Dict[str, float] = {}
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()

        # --- daily returns for benchmark ETFs ---
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

        # --- rolling correlations for risk-regime detection ---
        _return_cache: Dict[str, List[float]] = {}

        def _get_returns(ticker: str) -> List[float]:
            if ticker in _return_cache:
                return _return_cache[ticker]
            rows = conn.execute(
                "SELECT close FROM daily_ohlcv WHERE symbol = ? "
                "ORDER BY date DESC LIMIT 25",
                [ticker],
            ).fetchall()
            if rows and len(rows) >= 5:
                closes = [_safe_float(r[0]) for r in reversed(rows) if r[0]]
                rets = [
                    (closes[i] / closes[i - 1] - 1)
                    for i in range(1, len(closes))
                    if closes[i - 1] > 0
                ]
            else:
                rets = []
            _return_cache[ticker] = rets
            return rets

        for (t1, t2), feat_key in corr_pairs.items():
            r1 = _get_returns(t1)
            r2 = _get_returns(t2)
            if len(r1) >= 5 and len(r2) >= 5:
                features[feat_key] = round(_rolling_correlation(r1, r2), 4)
            # else: key absent → agent detects missing data

        # --- VIX level (absolute, not just return) ---
        vix_row = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = 'VIX' "
            "ORDER BY date DESC LIMIT 1",
        ).fetchone()
        if vix_row:
            features["vix_level"] = _safe_float(vix_row[0])

        # --- ticker-vs-SPY beta and correlation ---
        if symbol:
            ticker_rets = _get_returns(symbol.upper())
            spy_rets = _get_returns("SPY")
            if len(ticker_rets) >= 5 and len(spy_rets) >= 5:
                corr = _rolling_correlation(ticker_rets, spy_rets)
                features["ticker_spy_correlation"] = round(corr, 4)
                # beta = cov(ticker, spy) / var(spy)
                n = min(len(ticker_rets), len(spy_rets), 20)
                tx = ticker_rets[-n:]
                sx = spy_rets[-n:]
                ms = sum(sx) / n
                cov = sum((ti - sum(tx) / n) * (si - ms) for ti, si in zip(tx, sx)) / n
                var_s = sum((si - ms) ** 2 for si in sx) / n
                if var_s > 1e-12:
                    features["beta"] = round(cov / var_s, 4)

        # --- sector breadth (count bullish sectors from XLK,XLF,XLV,XLE,XLI,XLY,XLP,XLU,XLC,XLRE,XLB) ---
        sectors = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLC", "XLRE", "XLB"]
        bullish = 0
        total = 0
        for sec in sectors:
            sec_rows = conn.execute(
                "SELECT close FROM daily_ohlcv WHERE symbol = ? "
                "ORDER BY date DESC LIMIT 6",
                [sec],
            ).fetchall()
            if sec_rows and len(sec_rows) >= 6:
                last_c = _safe_float(sec_rows[0][0])
                prev_5 = _safe_float(sec_rows[5][0])
                if prev_5 > 0:
                    total += 1
                    if last_c > prev_5:
                        bullish += 1
        if total > 0:
            features["sector_bullish_pct"] = round(100.0 * bullish / total, 1)

    except Exception as e:
        logger.warning("Intermarket features error: %s", e)
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


def _parse_utc_iso(s: str) -> Optional[datetime]:
    """Parse UTC ISO string to datetime; return None if invalid."""
    if not s:
        return None
    try:
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def aggregate(
    symbol: str,
    ts: Optional[datetime] = None,
    timeframe: str = "1d",
    persist: bool = False,
) -> FeatureVector:
    """Aggregate all features for a symbol from real providers; no mock data.

    When OHLCV is missing or stale, price/volume/volatility are left empty
    (no silent zeros). data_freshness and provider_health let the council
    distinguish fresh vs stale vs missing and degrade to HOLD.
    """
    if ts is None:
        ts = datetime.now(timezone.utc)
    ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts
    ts_iso = ts_utc.isoformat().replace("+00:00", "Z")

    def _build_sync():
        from concurrent.futures import ThreadPoolExecutor
        from app.features.providers import (
            fetch_ohlcv,
            fetch_regime,
            fetch_flow,
            fetch_indicators,
            fetch_intermarket,
            get_stale_bar_max_age_seconds,
        )
        try:
            from app.core.config import settings
            _nworkers = getattr(settings, "FEATURE_AGGREGATOR_WORKERS", 4)
        except Exception:
            _nworkers = 4

        provider_timeout = 5
        ohlcv_rows: List[Dict[str, Any]] = []
        last_bar_utc = ""
        ohlcv_ok = False
        ohlcv_error = ""
        regime_features: Dict[str, Any] = {}
        regime_ok = False
        regime_last = ""
        regime_error = ""
        flow_features: Dict[str, float] = {}
        flow_ok = False
        flow_last = ""
        flow_error = ""
        indicator_features: Dict[str, float] = {}
        indicators_ok = False
        indicators_last = ""
        indicators_error = ""
        intermarket_features: Dict[str, float] = {}
        intermarket_ok = False
        intermarket_last = ""
        intermarket_error = ""

        with ThreadPoolExecutor(max_workers=max(1, _nworkers), thread_name_prefix="feat") as pool:
            f_ohlcv = pool.submit(fetch_ohlcv, symbol.upper(), 60)
            f_regime = pool.submit(fetch_regime)
            f_flow = pool.submit(fetch_flow, symbol.upper())
            f_ind = pool.submit(fetch_indicators, symbol.upper())
            f_int = pool.submit(fetch_intermarket, symbol.upper())

            try:
                ohlcv_rows, last_bar_utc, ohlcv_ok, ohlcv_error = f_ohlcv.result(timeout=provider_timeout)
            except Exception as e:
                logger.warning("OHLCV provider timeout/error for %s: %s", symbol, e)
                ohlcv_error = f"timeout:{type(e).__name__}"
            try:
                regime_features, regime_last, regime_ok, regime_error = f_regime.result(timeout=provider_timeout)
            except Exception as e:
                logger.warning("Regime provider timeout/error: %s", e)
                regime_features = {"regime": "unknown", "regime_confidence": 0.0}
                regime_error = f"timeout:{type(e).__name__}"
            try:
                flow_features, flow_last, flow_ok, flow_error = f_flow.result(timeout=provider_timeout)
            except Exception as e:
                logger.warning("Flow provider timeout/error for %s: %s", symbol, e)
                flow_error = f"timeout:{type(e).__name__}"
            try:
                indicator_features, indicators_last, indicators_ok, indicators_error = f_ind.result(timeout=provider_timeout)
            except Exception as e:
                logger.warning("Indicators provider timeout/error for %s: %s", symbol, e)
                indicators_error = f"timeout:{type(e).__name__}"
            try:
                intermarket_features, intermarket_last, intermarket_ok, intermarket_error = f_int.result(timeout=provider_timeout)
            except Exception as e:
                logger.warning("Intermarket provider timeout/error: %s", e)
                intermarket_error = f"timeout:{type(e).__name__}"

        # Only compute price/volume/volatility/cycle from real OHLCV; no zero defaults when missing
        if not ohlcv_ok or not ohlcv_rows:
            if not ohlcv_error:
                ohlcv_error = "no_ohlcv"
            logger.info("Feature aggregation: no OHLCV for %s (%s); omitting price/volume/volatility", symbol, ohlcv_error)
        price_features = _compute_price_features(ohlcv_rows) if ohlcv_rows else {}
        volume_features = _compute_volume_features(ohlcv_rows) if ohlcv_rows else {}
        volatility_features = _compute_volatility_features(ohlcv_rows) if len(ohlcv_rows) >= 2 else {}
        cycle_features = _get_cycle_features(ohlcv_rows) if ohlcv_rows else {}
        extended = _compute_extended_indicators(ohlcv_rows) if ohlcv_rows else {}
        for k, v in extended.items():
            if k not in indicator_features:
                indicator_features[k] = v

        # Strip sentinel keys from indicator_features if provider failed
        indicator_features = {k: v for k, v in indicator_features.items() if not k.startswith("_")}

        # Data freshness: bar age and staleness
        stale_threshold = get_stale_bar_max_age_seconds()
        now_utc = datetime.now(timezone.utc)
        last_dt = _parse_utc_iso(last_bar_utc)
        age_seconds = (now_utc - last_dt).total_seconds() if last_dt else float("inf")
        is_stale = (not last_bar_utc) or (age_seconds > stale_threshold)
        stale_reason = ""
        if not last_bar_utc:
            stale_reason = "no_bar"
        elif is_stale:
            stale_reason = "stale_bar"

        data_freshness = {
            "last_bar_utc": last_bar_utc or "",
            "age_seconds": round(age_seconds, 1) if last_bar_utc else None,
            "is_stale": is_stale,
            "stale_reason": stale_reason,
        }

        provider_health = {
            "ohlcv": {"ok": ohlcv_ok, "last_updated_utc": last_bar_utc, "error": ohlcv_error or None, "stale": is_stale},
            "regime": {"ok": regime_ok, "last_updated_utc": regime_last, "error": regime_error or None},
            "flow": {"ok": flow_ok, "last_updated_utc": flow_last, "error": flow_error or None},
            "indicators": {"ok": indicators_ok, "last_updated_utc": indicators_last, "error": indicators_error or None},
            "intermarket": {"ok": intermarket_ok, "last_updated_utc": intermarket_last, "error": intermarket_error or None},
        }

        is_sufficient = ohlcv_ok and bool(ohlcv_rows) and not is_stale
        missing_data_reason = ""
        if not ohlcv_ok or not ohlcv_rows:
            missing_data_reason = ohlcv_error or "no_ohlcv"
        elif is_stale:
            missing_data_reason = "stale_ohlcv"

        return FeatureVector(
            symbol=symbol.upper(),
            timestamp=ts_iso,
            timeframe=timeframe,
            price_features=price_features,
            volume_features=volume_features,
            volatility_features=volatility_features,
            regime_features=regime_features,
            flow_features=flow_features,
            indicator_features=indicator_features,
            intermarket_features=intermarket_features,
            cycle_features=cycle_features,
            data_freshness=data_freshness,
            provider_health=provider_health,
        ), is_sufficient, missing_data_reason, provider_health, data_freshness

    result = await asyncio.to_thread(_build_sync)
    fv = result[0]
    is_sufficient = result[1]
    missing_data_reason = result[2]
    provider_health = result[3]
    data_freshness = result[4]

    merged = {}
    merged.update(fv.price_features)
    merged.update(fv.volume_features)
    merged.update(fv.volatility_features)
    merged.update(fv.regime_features)
    merged.update(fv.flow_features)
    merged.update(fv.indicator_features)
    merged.update(fv.intermarket_features)
    merged.update(fv.cycle_features)
    fv.data_quality = _compute_data_quality(
        merged,
        is_sufficient=is_sufficient,
        missing_data_reason=missing_data_reason,
        provider_health=provider_health,
        data_freshness=data_freshness,
    )

    if persist:
        try:
            from app.data.feature_store import feature_store
            feature_store.store_features(symbol, ts_utc, timeframe, merged)
        except Exception as e:
            logger.warning("Failed to persist features for %s: %s", symbol, e)

    # Optional: augment with live Finviz quote when enabled (async; no mock; skip on failure)
    try:
        from app.core.config import settings
        if getattr(settings, "FEATURE_USE_FINVIZ_LIVE", False) and fv.price_features and symbol:
            from app.services.finviz_service import FinvizService
            svc = FinvizService()
            quotes = await svc.get_quote_data(ticker=symbol.upper(), timeframe="d", duration="d1")
            if quotes and isinstance(quotes, (list, dict)):
                q = quotes[0] if isinstance(quotes, list) and quotes else quotes
                close_val = q.get("close") or q.get("Close")
                if close_val is not None:
                    fv.price_features["last_close"] = _safe_float(close_val)
                    merged["last_close"] = fv.price_features["last_close"]
    except Exception as e:
        logger.debug("Optional Finviz live quote skipped for %s: %s", symbol, e)

    logger.debug(
        "Aggregated %d features for %s; sufficient=%s",
        fv.to_dict()["feature_count"], symbol, is_sufficient,
    )
    return fv
