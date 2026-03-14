"""Signals API: ML predictions for buy/sell timing (research doc)."""

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_auth
from app.schemas.signals import Signal, SignalsResponse, ActiveSignalResponse
from app.data.storage import get_conn
from app.models.inference import load_model, make_signals_for_date
from app.websocket_manager import broadcast_ws
from app.services.kelly_position_sizer import KellyPositionSizer

_kelly_sizer = KellyPositionSizer(max_allocation=0.10)

logger = logging.getLogger(__name__)

# ── ATR multipliers by pattern type ──────────────────────────────────────────
# RSI extreme patterns: tighter stops (mean reversion, quick snapback)
# Momentum/breakout: wider stops (trend following, needs room to breathe)
_PATTERN_ATR_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "rsi_extreme":      {"stop": 1.5, "target": 2.5},
    "rsi_oversold":     {"stop": 1.5, "target": 2.5},
    "rsi_overbought":   {"stop": 1.5, "target": 2.5},
    "mean_reversion":   {"stop": 1.5, "target": 2.5},
    "momentum":         {"stop": 2.5, "target": 3.5},
    "breakout":         {"stop": 2.5, "target": 3.5},
    "volume_breakout":  {"stop": 2.5, "target": 3.5},
    "trend_following":  {"stop": 2.5, "target": 3.5},
    "breakout_consolidation": {"stop": 2.0, "target": 3.5},
    "divergence":       {"stop": 1.5, "target": 2.5},
    "gap_analysis":     {"stop": 1.5, "target": 2.0},
    "multi_timeframe_confluence": {"stop": 2.0, "target": 3.0},
}
_DEFAULT_ATR_MULT = {"stop": 2.0, "target": 3.0}


def _fetch_atr_for_symbol(symbol: str) -> Optional[float]:
    """Fetch latest ATR-14 from DuckDB technical_indicators table.

    This is a SYNCHRONOUS function — must be called via asyncio.to_thread()
    from async contexts to avoid blocking the event loop.
    """
    try:
        from app.data.duckdb_storage import duckdb_store
        cursor = duckdb_store.get_thread_cursor()
        row = cursor.execute(
            "SELECT atr_14 FROM technical_indicators "
            "WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            [symbol.upper()],
        ).fetchone()
        if row and row[0] is not None and row[0] > 0:
            return float(row[0])
    except Exception as e:
        logger.debug("ATR lookup failed for %s: %s", symbol, e)
    return None


def _fetch_atr_batch(symbols: list[str]) -> Dict[str, float]:
    """Fetch latest ATR-14 for multiple symbols in a single query.

    SYNCHRONOUS — call via asyncio.to_thread().
    """
    atr_map: Dict[str, float] = {}
    if not symbols:
        return atr_map
    try:
        from app.data.duckdb_storage import duckdb_store
        cursor = duckdb_store.get_thread_cursor()
        placeholders = ", ".join(["?"] * len(symbols))
        rows = cursor.execute(
            f"SELECT symbol, atr_14 FROM ("
            f"  SELECT symbol, atr_14, "
            f"    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn "
            f"  FROM technical_indicators "
            f"  WHERE symbol IN ({placeholders})"
            f") WHERE rn = 1",
            [s.upper() for s in symbols],
        ).fetchall()
        for row in rows:
            if row[1] is not None and row[1] > 0:
                atr_map[row[0]] = float(row[1])
    except Exception as e:
        logger.debug("Batch ATR lookup failed: %s", e)
    return atr_map


def _compute_atr_levels(
    entry: float,
    atr: float,
    direction: str,
    pattern: str = "",
) -> Dict[str, float]:
    """Compute entry/target/stop using ATR and pattern-specific multipliers."""
    pattern_lower = pattern.lower().strip()
    mult = _DEFAULT_ATR_MULT
    for key, m in _PATTERN_ATR_MULTIPLIERS.items():
        if key in pattern_lower:
            mult = m
            break

    if direction == "LONG":
        stop = round(entry - atr * mult["stop"], 2)
        target = round(entry + atr * mult["target"], 2)
    else:
        stop = round(entry + atr * mult["stop"], 2)
        target = round(entry - atr * mult["target"], 2)

    risk = abs(entry - stop)
    reward = abs(target - entry)
    r_mult = round(reward / risk, 1) if risk > 0 else 1.5

    return {"target": target, "stop": stop, "r_multiple": r_mult}


router = APIRouter()

FEATURE_COLS = ["return_1d", "ma_10_dist", "ma_20_dist", "vol_20", "vol_rel"]
# Model path: backend/models/artifacts or project root models/artifacts
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_ARTIFACTS = _BACKEND_DIR / "models" / "artifacts"
DEFAULT_MODEL_PATH = MODEL_ARTIFACTS / "lstm_daily_latest.pt"


def _get_raw_signals_and_feats(as_of: date | None = None):
    """Shared logic: load feats, model, and produce raw signal dicts. Returns (raw_signals, feats) or (None, None) on failure."""
    if as_of is None:
        as_of = date.today()
    try:
        conn = get_conn()
        feats = conn.execute("SELECT * FROM daily_features").df()
        conn.close()
    except Exception as e:
        logger.warning("Failed to load daily_features from DuckDB: %s", e)
        return None, None
    if feats is None or feats.empty:
        return None, None
    if not Path(str(DEFAULT_MODEL_PATH)).exists():
        return None, None
    try:
        model = load_model(str(DEFAULT_MODEL_PATH), num_features=len(FEATURE_COLS))
    except Exception as e:
        logger.warning("Failed to load ML model from %s: %s", DEFAULT_MODEL_PATH, e)
        return None, None
    raw_signals = make_signals_for_date(model, feats, FEATURE_COLS, as_of)
    return raw_signals, feats


@router.post("/", response_model=SignalsResponse, dependencies=[Depends(require_auth)])
async def trigger_signals(as_of: date | None = None):
    """
    Trigger a fresh signal scan. Same logic as GET but semantically used
    by the Dashboard "Run Scan" button to force re-evaluation.
    """
    return await get_signals(as_of=as_of)


@router.get("/", response_model=None)
async def get_signals(as_of: date | None = None):
    """
    Return daily signals from all available sources:
    1. LSTM model + daily_features (when available)
    2. TurboScanner real-time scan signals (always available when backend is running)
    3. EventDrivenSignalEngine signals (from real-time bar processing)

    Returns signals formatted for Dashboard consumption with score, direction,
    entry/target/stop, scores breakdown, kelly sizing, etc.
    """
    if as_of is None:
        as_of = date.today()

    # Try ML model signals first (run sync DB query in thread)
    raw_signals, _ = await asyncio.to_thread(_get_raw_signals_and_feats, as_of)
    if raw_signals and len(raw_signals) > 0:
        signals = []
        for s in raw_signals:
            action = "BUY" if s["prob_up"] > 0.6 else "HOLD"
            prob = s["prob_up"]
            kelly = _kelly_sizer.calculate(
                win_rate=prob, avg_win_pct=0.035, avg_loss_pct=0.015,
            )
            signals.append(
                Signal(
                    symbol=s["symbol"], date=as_of, prob_up=prob, action=action,
                    edge=kelly.edge, kelly_fraction=kelly.raw_kelly,
                    position_size_pct=kelly.final_pct, expected_value=kelly.edge * prob,
                )
            )
        response = SignalsResponse(as_of=as_of, signals=signals)
        await broadcast_ws("signals", {
            "type": "signals_updated",
            "count": len(signals),
            "as_of": str(as_of),
        })
        return response

    # Fall back to TurboScanner real-time signals (real market data, not mock)
    dashboard_signals = []
    try:
        from app.services.turbo_scanner import get_turbo_scanner
        scanner = get_turbo_scanner()
        scan_signals = scanner.get_signals(limit=50)
        # De-duplicate by symbol, keep highest score
        seen = {}
        for ss in scan_signals:
            sym = ss.get("symbol", "")
            if not sym:
                continue
            if sym not in seen or ss.get("score", 0) > seen[sym].get("score", 0):
                seen[sym] = ss

        # Batch-fetch ATR for all symbols (single DuckDB query in thread)
        all_syms = list(seen.keys())
        atr_map = await asyncio.to_thread(_fetch_atr_batch, all_syms)

        for sym, ss in seen.items():
            raw_score = ss.get("score", 0)
            score_100 = round(raw_score * 100) if raw_score <= 1.0 else round(raw_score)
            direction = "LONG" if ss.get("direction", "").lower() == "bullish" else (
                "SHORT" if ss.get("direction", "").lower() == "bearish" else "LONG"
            )
            price = ss.get("data", {}).get("close", ss.get("data", {}).get("price", 0))
            entry = round(price, 2) if price else 0
            pattern = ss.get("signal_type", "")

            # ATR-based entry/target/stop (fall back to fixed % if no ATR)
            atr_val = atr_map.get(sym)
            if entry and atr_val:
                levels = _compute_atr_levels(entry, atr_val, direction, pattern)
                target = levels["target"]
                stop = levels["stop"]
                r_mult = levels["r_multiple"]
                # Compute actual avg_win / avg_loss from the ATR levels
                avg_win_pct = abs(target - entry) / entry if entry else 0.035
                avg_loss_pct = abs(entry - stop) / entry if entry else 0.015
            else:
                # Fallback: fixed percentage when no ATR data available
                target = round(entry * (1.03 if direction == "LONG" else 0.97), 2) if entry else 0
                stop = round(entry * (0.98 if direction == "LONG" else 1.02), 2) if entry else 0
                r_mult = round((abs(target - entry) / abs(entry - stop)), 1) if entry and stop and entry != stop else 1.5
                avg_win_pct = 0.035
                avg_loss_pct = 0.015

            kelly = _kelly_sizer.calculate(
                win_rate=max(0.5, score_100 / 100), avg_win_pct=avg_win_pct, avg_loss_pct=avg_loss_pct,
            )
            dashboard_signals.append({
                "symbol": sym,
                "direction": direction,
                "score": score_100,
                "scores": {
                    "technical": round(score_100 * 0.9),
                    "ml": 0,
                    "sentiment": 0,
                    "regime": ss.get("data", {}).get("regime_score", 0),
                    "breakout": ss.get("data", {}).get("breakout_score", 0),
                    "rebound": ss.get("data", {}).get("rebound_score", 0),
                    "meanReversion": ss.get("data", {}).get("mean_reversion_score", 0),
                },
                "entry": entry,
                "target": target,
                "stop": stop,
                "rMultiple": r_mult,
                "kellyPercent": round(kelly.final_pct * 100, 1),
                "momentum": ss.get("data", {}).get("momentum", 0) or round(ss.get("data", {}).get("ret_5d", 0) * 100, 1),
                "volSpike": ss.get("data", {}).get("vol_ratio", 0) or round(ss.get("data", {}).get("gap_pct", 0) * 100, 1),
                "sector": ss.get("data", {}).get("sector", ""),
                "pattern": ss.get("signal_type", ""),
                "leadAgent": ss.get("source", "turbo_scanner"),
                "swarmVote": direction,
                "topShap": ss.get("reasoning", "")[:40],
                "newsImpact": "",
                "expPnL": 0,
                "detected_at": ss.get("detected_at", ""),
            })
    except Exception as e:
        logger.warning("TurboScanner signals unavailable: %s", e)

    # When no ML and no TurboScanner signals, return minimal placeholder so Dashboard shows data flow
    if not dashboard_signals:
        for sym in ("SPY", "QQQ", "AAPL"):
            dashboard_signals.append({
                "symbol": sym,
                "direction": "LONG",
                "score": 50,
                "scores": {"technical": 50, "ml": 0, "sentiment": 0, "regime": 0, "breakout": 0, "rebound": 0, "meanReversion": 0},
                "entry": 0,
                "target": 0,
                "stop": 0,
                "rMultiple": 1.5,
                "kellyPercent": 10,
                "momentum": 0,
                "volSpike": 0,
                "sector": "",
                "pattern": "placeholder",
                "leadAgent": "system",
                "swarmVote": "LONG",
                "topShap": "Waiting for live scan",
                "newsImpact": "",
                "expPnL": 0,
                "detected_at": "",
            })

    # Sort by score descending
    dashboard_signals.sort(key=lambda x: x.get("score", 0), reverse=True)
    result = {"as_of": str(as_of), "signals": dashboard_signals}
    if dashboard_signals:
        await broadcast_ws("signals", {
            "type": "signals_updated",
            "count": len(dashboard_signals),
            "as_of": str(as_of),
        })
    return result


@router.get("/{symbol}/technicals")
async def get_technicals(symbol: str, as_of: date | None = None):
    """Technical indicators for a symbol (Dashboard). Stub when no features; real when available."""
    symbol = symbol.upper().strip() if symbol else ""
    raw_signals, feats = _get_raw_signals_and_feats(as_of)
    def _stub_technicals(sym: str, ind: dict | None = None):
        ind = ind or {}
        ma20 = ind.get("ma_20_dist")
        ema20_val = ind.get("ema20") or (f"{float(ma20):.2f}" if ma20 is not None else "0")
        # Always return displayable values for Dashboard (no None so UI shows 0 or placeholder)
        return {
            "symbol": sym or "?",
            "indicators": ind,
            "technicals": {
                "rsi": ind.get("rsi") if ind.get("rsi") is not None else 0,
                "macd": ind.get("macd") if ind.get("macd") is not None else 0,
                "bb": ind.get("bb") if ind.get("bb") is not None else "0",
                "vwap": ind.get("vwap") if ind.get("vwap") is not None else 0,
                "ema20": ema20_val,
                "sma50": ind.get("sma50") if ind.get("sma50") is not None else 0,
                "adx": ind.get("adx") if ind.get("adx") is not None else 0,
                "stoch": ind.get("stoch") if ind.get("stoch") is not None else 0,
                "driftScore": ind.get("driftScore") if ind.get("driftScore") is not None else 0,
            },
            "score": 50 if ind else 0,
            "momentum": "neutral",
            "breakout": 0,
            "meanReversion": 0,
            "volume": 0,
        }

    if feats is None or feats.empty or "symbol" not in feats.columns:
        return _stub_technicals(symbol or "?")
    syms = feats["symbol"].astype(str).str.upper().tolist()
    if symbol and symbol not in syms:
        return _stub_technicals(symbol)
    try:
        row = feats[feats["symbol"].astype(str).str.upper() == symbol].iloc[-1]
        ind = {
            "ma_10_dist": float(row.get("ma_10_dist", 0)),
            "ma_20_dist": float(row.get("ma_20_dist", 0)),
            "vol_20": float(row.get("vol_20", 0)),
            "vol_rel": float(row.get("vol_rel", 0)),
            "return_1d": float(row.get("return_1d", 0)),
        }
        return _stub_technicals(symbol, ind)
    except Exception:
        return _stub_technicals(symbol)


@router.get("/active/{symbol}", response_model=ActiveSignalResponse)
def get_active_signal(symbol: str, as_of: date | None = None):
    """
    Return the active signal for a single symbol, or 404 if none.
    Real data only (LSTM + daily_features). Used by ExecutionDeck.
    """
    symbol = symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol required")
    raw_signals, feats = _get_raw_signals_and_feats(as_of)
    if raw_signals is None or len(raw_signals) == 0:
        raise HTTPException(status_code=404, detail="No signals available (run daily_update and ensure model exists)")
    match = next((s for s in raw_signals if s["symbol"].upper() == symbol), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"No active signal for {symbol}")
    action = "BUY" if match["prob_up"] > 0.6 else "HOLD"
    # Entry = latest close for this symbol from features
    sym_feats = feats[feats["symbol"].str.upper() == symbol].sort_values("date")
    if sym_feats.empty or "close" not in sym_feats.columns:
        entry = 0.0
    else:
        entry = float(sym_feats["close"].iloc[-1])
    # Simple placeholders when we don't have levels from strategy
    target = entry * 1.02 if entry else 0.0
    stop = entry * 0.98 if entry else 0.0
    risk_reward = 2.0
    as_of_val = as_of if as_of else date.today()
    return ActiveSignalResponse(
        symbol=match["symbol"],
        date=as_of_val,
        prob_up=match["prob_up"],
        action=action,
        entry=entry,
        target=target,
        stop=stop,
        risk_reward=risk_reward,
        type=action,
        confidence=round(match["prob_up"] * 100),
    )


@router.get("/heatmap")
async def get_signals_heatmap():
    """
    Return composite scores for heatmap from real LSTM signals only.
    Empty list when no model/features. Used by Signal Heatmap page.
    """
    raw_signals, _ = _get_raw_signals_and_feats()
    if not raw_signals or len(raw_signals) == 0:
        return []
    heatmap_data = []
    for sig in raw_signals[:20]:
        prob_up = sig.get("prob_up", 0.5)
        composite_score = prob_up * 100
        heatmap_data.append(
            {
                "ticker": sig.get("symbol", "UNKNOWN"),
                "sector": "Technology",
                "compositeScore": round(composite_score, 1),
                "aiAnalysis": f"ML probability: {prob_up:.2f}",
                "components": {
                    "technical": round(composite_score * 0.9, 0),
                    "ml": round(composite_score, 0),
                    "sentiment": round(composite_score * 0.85, 0),
                    "volume": round(composite_score * 0.8, 0),
                    "aiReasoning": round(composite_score * 0.95, 0),
                },
                "expectedMove": round(composite_score / 20, 1),
                "confidence": prob_up,
                "profitPotential": (
                    "HIGH"
                    if composite_score >= 80
                    else "MODERATE" if composite_score >= 60 else "LOW"
                ),
                "timeframe": "1-3 days",
            }
        )
    return heatmap_data


@router.get("/kelly-ranked")
async def get_kelly_ranked():
    """
    Return signals ranked by Kelly edge * signal quality.
    Best money-making opportunities first.
    """
    raw_signals, _ = _get_raw_signals_and_feats()
    if not raw_signals or len(raw_signals) == 0:
        return {"kelly": [], "kellyRanked": []}

    ranked = []
    for s in raw_signals:
        prob = s.get("prob_up", 0.5)
        kelly = _kelly_sizer.calculate(
            win_rate=prob,
            avg_win_pct=0.035,
            avg_loss_pct=0.015,
        )
        edge = kelly.edge
        quality = min(1.0, prob * 1.5)  # Signal quality proxy
        if edge > 0 and quality > 0.3:
            ranked.append({
                "symbol": s["symbol"],
                "kelly_edge": round(edge, 4),
                "signal_quality": round(quality, 3),
                "kelly_score": round(edge * quality, 4),
                "kelly_fraction": round(kelly.raw_kelly, 4),
                "position_size_pct": round(kelly.final_pct, 4),
                "optimalFraction": round(kelly.final_pct, 4),
                "prob_up": round(prob, 3),
                "action": "BUY" if prob > 0.6 else "HOLD",
            })

    ranked.sort(key=lambda x: x["kelly_score"], reverse=True)
    top = ranked[:20]
    return {"kelly": top, "kellyRanked": top}
