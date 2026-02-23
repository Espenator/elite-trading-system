"""
Signal Generation Agent -- technical analysis and composite scores (0-100).

Takes raw data from Market Data Agent (symbol_universe). Optionally uses Finviz
quote data for price. Merges OpenClaw regime + candidate scores when available.
Applies momentum and simple pattern logic; outputs composite signal scores
0-100 for logging and downstream (ML, alerts).
"""
import logging
from typing import Dict, List, Optional, Tuple

from app.modules.symbol_universe import get_tracked_symbols

logger = logging.getLogger(__name__)

AGENT_NAME = "Signal Generation Agent"

# Max symbols to score per tick (avoid rate limits and latency)
DEFAULT_MAX_SYMBOLS = 20
# Min composite score to mention in log (e.g. "above 70")
MIN_SCORE_TO_REPORT = 70

# Regime multipliers: scale final score by market regime from OpenClaw
_REGIME_MULTIPLIERS: Dict[str, float] = {
    "BULLISH": 1.10,
    "RISK_ON": 1.05,
    "NEUTRAL": 1.00,
    "RISK_OFF": 0.90,
    "BEARISH": 0.80,
    "CRISIS": 0.65,
    "UNKNOWN": 1.00,
}


def _numeric(val, default: float = 0.0) -> float:
    """Parse a value to float; strip commas and $."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("$", "")
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _compute_composite_score(quotes: List[dict]) -> Tuple[float, str]:
    """
    Compute composite signal score 0-100 from quote rows.
    Expects list of dicts with Open/Close/High/Low (case-flexible).
    Returns (score, label) e.g. (87, "Bull Flag").
    """
    if not quotes or not isinstance(quotes, list):
        return 50.0, "No data"

    # Normalize keys (Finviz CSV may use different casing)
    rows = []
    for r in quotes:
        if not isinstance(r, dict):
            continue
        row = {}
        for k, v in r.items():
            row[k.strip().lower() if isinstance(k, str) else k] = v
        rows.append(row)

    if not rows:
        return 50.0, "No data"

    # Prefer last row for current bar; use first/last for momentum
    last = rows[-1]
    open_val = _numeric(last.get("open"))
    close_val = _numeric(last.get("close"))
    high_val = _numeric(last.get("high"))
    low_val = _numeric(last.get("low"))

    # Momentum: (close - open) / open * 50, capped to +/-25, then 50 + that
    if open_val and open_val > 0:
        momentum_pct = (close_val - open_val) / open_val * 100
        momentum_score = max(-25, min(25, momentum_pct * 0.5))
    else:
        momentum_score = 0.0

    # Simple pattern: bull candle = close > open
    if close_val > open_val:
        pattern_score = 15
        pattern_label = "Bull"
    elif close_val < open_val:
        pattern_score = -15
        pattern_label = "Bear"
    else:
        pattern_score = 0
        pattern_label = "Doji"

    # Range: high-low as volatility proxy (wider range = more volatility, small bonus/penalty)
    if low_val and low_val > 0 and high_val > low_val:
        range_pct = (high_val - low_val) / low_val * 100
        range_score = max(-5, min(5, (range_pct - 2) * 0.5))
    else:
        range_score = 0.0

    composite = 50.0 + momentum_score + pattern_score + range_score
    composite = max(0.0, min(100.0, composite))
    label = pattern_label + " candle" if pattern_label != "No data" else "Neutral"
    return round(composite, 1), label


async def _get_openclaw_context() -> Tuple[str, Dict[str, float]]:
    """
    Fetch OpenClaw regime + candidate scores (ticker -> composite_score).
    Returns (regime_state, {ticker: openclaw_score}).
    Gracefully returns defaults if bridge unavailable.
    """
    try:
        from app.services.openclaw_bridge_service import openclaw_bridge

        health = await openclaw_bridge.get_health()
        if not health.get("connected"):
            return "UNKNOWN", {}

        regime = await openclaw_bridge.get_regime()
        candidates = await openclaw_bridge.get_top_candidates(n=50)

        regime_state = regime.get("state", "UNKNOWN")
        claw_scores: Dict[str, float] = {}
        for c in candidates:
            ticker = c.get("ticker")
            score = c.get("composite_score")
            if ticker and score is not None:
                claw_scores[ticker] = float(score)

        return regime_state, claw_scores
    except Exception as e:
        logger.debug("OpenClaw context unavailable: %s", e)
        return "UNKNOWN", {}


async def run_tick(
    *,
    max_symbols: int = DEFAULT_MAX_SYMBOLS,
    use_quote_data: bool = True,
    use_openclaw: bool = True,
) -> List[Tuple[str, str]]:
    """
    Run one Signal Generation tick: take symbols from Market Data Agent (symbol_universe),
    apply momentum/pattern logic, merge OpenClaw scores + regime, produce composite scores.
    Returns list of (message, level).
    """
    entries: List[Tuple[str, str]] = []

    symbols = get_tracked_symbols()
    if not symbols:
        entries.append(
            (
                "No symbols from Market Data Agent -- run Agent 1 first or check symbol_universe",
                "warning",
            )
        )
        return entries

    # Fetch OpenClaw regime + candidate overlay
    regime_state = "UNKNOWN"
    claw_scores: Dict[str, float] = {}
    if use_openclaw:
        regime_state, claw_scores = await _get_openclaw_context()
        if claw_scores:
            entries.append(
                (
                    f"OpenClaw overlay: regime={regime_state}, {len(claw_scores)} candidate scores loaded",
                    "info",
                )
            )

    sample = symbols[:max_symbols]
    scored = []
    errors = 0

    finviz_svc = None
    if use_quote_data:
        try:
            from app.services.finviz_service import FinvizService

            finviz_svc = FinvizService()
        except Exception as e:
            logger.warning("Finviz not available for signal engine: %s", e)
            entries.append(
                ("Finviz quote data unavailable (check FINVIZ_API_KEY)", "info")
            )
            use_quote_data = False

    regime_mult = _REGIME_MULTIPLIERS.get(regime_state, 1.0)

    for symbol in sample:
        quotes = []
        if use_quote_data and finviz_svc:
            try:
                quotes = await finviz_svc.get_quote_data(
                    ticker=symbol,
                    timeframe="d",
                    duration="d5",
                )
            except Exception as e:
                logger.debug("Quote fetch failed for %s: %s", symbol, e)
                errors += 1

        ta_score, label = _compute_composite_score(quotes)

        # Blend with OpenClaw candidate score if available (60/40 weight)
        claw_score = claw_scores.get(symbol)
        if claw_score is not None:
            blended = (ta_score * 0.4) + (claw_score * 0.6)
            label = f"{label}+Claw"
        else:
            blended = ta_score

        # Apply regime multiplier
        final_score = max(0.0, min(100.0, blended * regime_mult))
        scored.append((symbol, round(final_score, 1), label))

    # Sort by score descending; build log messages
    scored.sort(key=lambda x: -x[1])
    above = [t for t in scored if t[1] >= MIN_SCORE_TO_REPORT]

    if above:
        top = above[0]
        entries.append(
            (
                f"Generated composite score {int(top[1])} for {top[0]} ({top[2]})",
                "success",
            )
        )

    entries.append(
        (
            f"Momentum algo applied to {len(sample)} symbols, {len(above)} above {MIN_SCORE_TO_REPORT}"
            + (f" ({errors} quote errors)" if errors else "")
            + (f" [regime={regime_state}, mult={regime_mult:.2f}]" if use_openclaw else ""),
            "info",
        )
    )
    return entries
