"""Feature data providers — DuckDB-backed fetches with freshness and health.

Each provider returns data plus last_updated_utc and ok/error so the aggregator
can surface provider_health and data_freshness for the council. No mock data;
empty or failed providers return empty dict and ok=False with a clear reason.

Usage:
    from app.features.providers import fetch_ohlcv, get_stale_bar_max_age_seconds
    rows, last_utc, ok, err = fetch_ohlcv("AAPL", limit=60)
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default: consider daily bar stale if older than 2 days (no trade on stale data)
DEFAULT_STALE_BAR_MAX_AGE_SECONDS = 2 * 86400


def get_stale_bar_max_age_seconds() -> float:
    """Configurable max age for bar data before considered stale (seconds)."""
    try:
        from app.core.config import settings
        return float(getattr(settings, "FEATURE_STALE_BAR_MAX_AGE_SECONDS", DEFAULT_STALE_BAR_MAX_AGE_SECONDS))
    except Exception:
        return DEFAULT_STALE_BAR_MAX_AGE_SECONDS


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        v = float(val)
        return v if (v == v and abs(v) != float("inf")) else default
    except (TypeError, ValueError):
        return default


def _date_to_utc_iso(d: date) -> str:
    """Normalize date to UTC end-of-day ISO string."""
    if d is None:
        return ""
    dt = datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


@dataclass
class ProviderResult:
    """Result of a single provider fetch: data, freshness, and health."""
    data: Any  # dict or list
    last_updated_utc: str  # ISO or ""
    ok: bool
    error_message: str = ""
    provider_name: str = ""


def fetch_ohlcv(symbol: str, limit: int = 60) -> Tuple[List[Dict[str, Any]], str, bool, str]:
    """Fetch OHLCV rows from DuckDB and latest bar date.

    Returns:
        (rows, last_bar_utc_iso, ok, error_message)
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        df = conn.execute(
            """SELECT date, open, high, low, close, volume
               FROM daily_ohlcv
               WHERE symbol = ?
               ORDER BY date DESC
               LIMIT ?""",
            [symbol.upper(), limit],
        ).fetchdf()
        if df is None or df.empty:
            logger.debug("No OHLCV for %s", symbol)
            return [], "", False, "no_ohlcv"

        # Last bar date for freshness
        last_date = df["date"].iloc[0]
        if hasattr(last_date, "date"):
            last_date = last_date.date() if hasattr(last_date, "date") else last_date
        last_utc = _date_to_utc_iso(last_date)

        rows = df.sort_values("date").to_dict("records")
        # Normalize date to string for JSON/council
        for r in rows:
            if "date" in r and hasattr(r["date"], "isoformat"):
                r["date"] = r["date"].isoformat() if hasattr(r["date"], "isoformat") else str(r["date"])
        return rows, last_utc, True, ""
    except Exception as e:
        logger.warning("OHLCV provider failed for %s: %s", symbol, e)
        return [], "", False, f"ohlcv_error:{type(e).__name__}"


def fetch_regime() -> Tuple[Dict[str, Any], str, bool, str]:
    """Fetch regime snapshot (VIX + SPY trend) from DuckDB.

    Returns:
        (regime_dict, last_utc_iso, ok, error_message)
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()

        vix_row = conn.execute(
            "SELECT close, date FROM daily_ohlcv WHERE symbol = 'VIX' ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if not vix_row:
            return {"regime": "unknown", "regime_confidence": 0.0}, "", False, "no_vix"

        vix = _safe_float(vix_row[0])
        last_date = vix_row[1]
        last_utc = _date_to_utc_iso(last_date) if last_date else ""

        spy_rows = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = 'SPY' ORDER BY date DESC LIMIT 21"
        ).fetchall()
        spy_return_20d = 0.0
        if len(spy_rows) >= 21 and spy_rows[20][0]:
            spy_return_20d = (spy_rows[0][0] - spy_rows[20][0]) / spy_rows[20][0]
        uptrend = spy_return_20d > 0.01
        downtrend = spy_return_20d < -0.01

        if vix <= 0:
            return {"regime": "unknown", "regime_confidence": 0.0, "vix_close": 0}, last_utc, True, ""

        if vix > 30:
            regime, conf = "bearish", 0.8
        elif vix > 20:
            regime, conf = ("volatile", 0.7) if downtrend else ("choppy", 0.5)
        elif vix > 15:
            regime, conf = "normal", 0.5
        else:
            regime, conf = ("bullish", 0.8) if uptrend else ("trending_up", 0.6)

        return {
            "regime": regime,
            "regime_confidence": conf,
            "vix_close": vix,
            "spy_return_20d": round(spy_return_20d, 4),
        }, last_utc, True, ""
    except Exception as e:
        logger.warning("Regime provider failed: %s", e)
        return {"regime": "unknown", "regime_confidence": 0.0}, "", False, f"regime_error:{type(e).__name__}"


def fetch_flow(symbol: str) -> Tuple[Dict[str, float], str, bool, str]:
    """Fetch options flow features from DuckDB.

    Returns:
        (flow_dict, last_utc_iso, ok, error_message)
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        row = conn.execute(
            """SELECT call_volume, put_volume, net_premium, pcr_volume, total_premium, date
               FROM options_flow
               WHERE symbol = ?
               ORDER BY date DESC LIMIT 1""",
            [symbol.upper()],
        ).fetchone()
        if not row:
            return {}, "", True, "no_flow_data"  # ok=True, just no row

        last_date = row[5] if len(row) > 5 else None
        last_utc = _date_to_utc_iso(last_date) if last_date else ""
        data = {
            "flow_call_volume": _safe_float(row[0]),
            "flow_put_volume": _safe_float(row[1]),
            "flow_net_premium": _safe_float(row[2]),
            "flow_pcr": _safe_float(row[3]),
            "flow_total_premium": _safe_float(row[4]),
        }
        return data, last_utc, True, ""
    except Exception as e:
        logger.warning("Flow provider failed for %s: %s", symbol, e)
        return {}, "", False, f"flow_error:{type(e).__name__}"


def fetch_indicators(symbol: str) -> Tuple[Dict[str, float], str, bool, str]:
    """Fetch technical indicators from DuckDB.

    Returns:
        (indicator_dict with ind_* keys, last_utc_iso, ok, error_message)
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        try:
            cols_df = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'technical_indicators'"
            ).fetchall()
            available_cols = {r[0] for r in cols_df} if cols_df else set()
        except Exception:
            available_cols = set()

        core_cols = [
            "rsi_14", "macd", "macd_signal", "macd_hist",
            "sma_20", "sma_50", "sma_200",
            "ema_9", "ema_21", "atr_14", "atr_21",
            "bb_upper", "bb_lower", "adx_14",
        ]
        extended_cols = [
            "ema_5", "ema_10", "ema_20",
            "bb_middle", "std_20",
            "rsi_14_prev",
            "relative_strength_spy",
            "rs_rank_percentile",
        ]
        query_cols = [c for c in core_cols + extended_cols if not available_cols or c in available_cols]
        if not query_cols:
            return {}, "", True, "no_indicator_columns"

        col_str = ", ".join(query_cols)
        row = conn.execute(
            f"SELECT date, {col_str} FROM technical_indicators WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [symbol.upper()],
        ).fetchone()
        if not row:
            return {}, "", True, "no_indicator_row"

        last_date = row[0]
        last_utc = _date_to_utc_iso(last_date) if last_date else ""
        result = {}
        for i, col in enumerate(query_cols):
            val = row[i + 1]
            if val is not None:
                result[f"ind_{col}"] = _safe_float(val)
        return result, last_utc, True, ""
    except Exception as e:
        logger.error("Indicator provider failed for %s: %s", symbol, e)
        return {}, "", False, f"indicator_error:{type(e).__name__}"


def fetch_intermarket(symbol: str) -> Tuple[Dict[str, float], str, bool, str]:
    """Fetch intermarket features (benchmarks, correlations, sector breadth) from DuckDB.

    Returns:
        (intermarket_dict, last_utc_iso from SPY, ok, error_message)
    """
    # Reuse _rolling_correlation from feature_aggregator to avoid circular import
    def _rolling_correlation(xs: List[float], ys: List[float], window: int = 20) -> float:
        n = min(len(xs), len(ys), window)
        if n < 5:
            return 0.0
        x, y = xs[-n:], ys[-n:]
        mx, my = sum(x) / n, sum(y) / n
        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        sx = sum((xi - mx) ** 2 for xi in x) ** 0.5
        sy = sum((yi - my) ** 2 for yi in y) ** 0.5
        if sx < 1e-12 or sy < 1e-12:
            return 0.0
        return cov / (sx * sy)

    try:
        from app.data.duckdb_storage import duckdb_store
        conn = duckdb_store.get_thread_cursor()
        benchmarks = {"SPY": "intermarket_spy", "VIX": "intermarket_vix", "DXY": "intermarket_dxy",
                      "TLT": "intermarket_tlt", "GLD": "intermarket_gld"}
        corr_pairs = {("SPY", "UVXY"): "spy_uvxy_correlation", ("SPY", "IEF"): "spy_ief_correlation",
                      ("SPY", "IWM"): "spy_iwm_correlation"}
        features: Dict[str, float] = {}
        return_cache: Dict[str, List[float]] = {}

        def get_returns(ticker: str) -> List[float]:
            if ticker in return_cache:
                return return_cache[ticker]
            rows = conn.execute(
                "SELECT close FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 25",
                [ticker],
            ).fetchall()
            if rows and len(rows) >= 5:
                closes = [_safe_float(r[0]) for r in reversed(rows) if r[0]]
                rets = [(closes[i] / closes[i - 1] - 1) for i in range(1, len(closes)) if closes[i - 1] > 0]
            else:
                rets = []
            return_cache[ticker] = rets
            return rets

        last_utc = ""
        for ticker, key in benchmarks.items():
            row = conn.execute(
                "SELECT close, date FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 2",
                [ticker],
            ).fetchall()
            if row and len(row) >= 2 and row[0][0] and row[1][0]:
                prev = _safe_float(row[1][0])
                if prev > 0:
                    features[f"{key}_return"] = (row[0][0] / prev) - 1
                    features[f"{key}_price"] = _safe_float(row[0][0])
                if not last_utc and row[0][1]:
                    last_utc = _date_to_utc_iso(row[0][1])

        for (t1, t2), feat_key in corr_pairs.items():
            r1, r2 = get_returns(t1), get_returns(t2)
            if len(r1) >= 5 and len(r2) >= 5:
                features[feat_key] = round(_rolling_correlation(r1, r2), 4)

        vix_row = conn.execute(
            "SELECT close FROM daily_ohlcv WHERE symbol = 'VIX' ORDER BY date DESC LIMIT 1"
        ).fetchone()
        if vix_row:
            features["vix_level"] = _safe_float(vix_row[0])

        if symbol:
            ticker_rets = get_returns(symbol.upper())
            spy_rets = get_returns("SPY")
            if len(ticker_rets) >= 5 and len(spy_rets) >= 5:
                features["ticker_spy_correlation"] = round(_rolling_correlation(ticker_rets, spy_rets), 4)
                n = min(len(ticker_rets), len(spy_rets), 20)
                tx, sx = ticker_rets[-n:], spy_rets[-n:]
                ms = sum(sx) / n
                cov = sum((ti - sum(tx) / n) * (si - ms) for ti, si in zip(tx, sx)) / n
                var_s = sum((si - ms) ** 2 for si in sx) / n
                if var_s > 1e-12:
                    features["beta"] = round(cov / var_s, 4)

        sectors = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLC", "XLRE", "XLB"]
        bullish = total = 0
        for sec in sectors:
            sec_rows = conn.execute(
                "SELECT close FROM daily_ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 6",
                [sec],
            ).fetchall()
            if sec_rows and len(sec_rows) >= 6 and sec_rows[5][0]:
                total += 1
                if sec_rows[0][0] > sec_rows[5][0]:
                    bullish += 1
        if total > 0:
            features["sector_bullish_pct"] = round(100.0 * bullish / total, 1)

        return features, last_utc or "", True, ""
    except Exception as e:
        logger.warning("Intermarket provider failed: %s", e)
        return {}, "", False, f"intermarket_error:{type(e).__name__}"
