#!/usr/bin/env python3
"""
OpenClaw Main Orchestrator v3.0 — Async Pipeline (Task 8c)

Fully async orchestrator replacing the synchronous v2.0.
Uses asyncio to run independent pipeline stages concurrently:
  - Pre-flight checks (regime, circuit breaker, heat)
  - Data collection (Finviz, UW, Discord, FOM) in parallel
  - Scoring pipeline (composite → ensemble → dynamic weights)
  - Smart entry + risk governor gating
  - Position monitoring loop
  - End-of-day reporting

Usage:
  python main.py                   # Full async pipeline
  python main.py --positions-only  # Monitor positions
  python main.py --report          # Performance report
  python main.py --stream          # Launch streaming engine
  python main.py --dashboard       # Start live dashboard
"""

import os
import sys
import json
import asyncio
import logging
import argparse
import signal
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

# ── Logging ──────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/openclaw.log", mode="a"),
    ]
)
logger = logging.getLogger("openclaw.main")
ET = ZoneInfo("America/New_York")


# ── Async Helpers ────────────────────────────────────────────

async def run_sync(func, *args, **kwargs):
    """Run a synchronous function in the default executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


class PipelineContext:
    """Shared state passed through pipeline stages."""

    def __init__(self):
        self.start_time = datetime.now(ET)
        self.regime: str = "neutral"
        self.regime_confidence: float = 0.0
        self.preflight_passed: bool = True
        self.circuit_breaker: dict = {}
        self.portfolio_heat: dict = {}
        self.session: dict = {}
        self.candidates: list = []
        self.tradeable: list = []
        self.positions: dict = {}
        self.bridge_result: dict = {}
        self.errors: list = []

    @property
    def elapsed(self) -> float:
        return (datetime.now(ET) - self.start_time).total_seconds()

    def to_dict(self) -> dict:
        return {
            "status": "COMPLETE" if self.preflight_passed else "DEGRADED",
            "elapsed_seconds": round(self.elapsed, 1),
            "regime": self.regime,
            "regime_confidence": round(self.regime_confidence, 2),
            "candidates_scored": len(self.candidates),
            "tradeable": len(self.tradeable),
            "open_positions": self.positions.get("open_positions", 0),
            "preflight_passed": self.preflight_passed,
            "errors": self.errors,
            "timestamp": datetime.now(ET).isoformat(),
        }


# ══════════════════════════════════════════════════════════════
# STAGE 1: PRE-FLIGHT (parallel sub-checks)
# ══════════════════════════════════════════════════════════════

async def check_circuit_breaker(ctx: PipelineContext) -> None:
    """Check daily P&L circuit breaker via position_manager."""
    try:
        from position_manager import PositionManager
        pm = PositionManager()
        breaker = await run_sync(pm.check_daily_circuit_breaker)
        ctx.circuit_breaker = breaker
        if breaker.get("breaker_hit"):
            ctx.preflight_passed = False
            logger.warning("Circuit breaker HIT: %s", breaker.get("action"))
        else:
            logger.info("Circuit breaker OK — Daily P&L: $%+.2f",
                        breaker.get("daily_pnl", 0))
    except Exception as e:
        ctx.errors.append(f"circuit_breaker: {e}")
        logger.warning("Circuit breaker check failed: %s", e)


async def check_portfolio_heat(ctx: PipelineContext) -> None:
    """Check portfolio heat and sector concentration."""
    try:
        from position_manager import PositionManager
        pm = PositionManager()
        heat = await run_sync(pm.calculate_portfolio_heat)
        ctx.portfolio_heat = heat
        if not heat.get("heat_ok", True):
            logger.warning("Portfolio heat HIGH: %.1f%%", heat.get("heat_pct", 0))
        else:
            logger.info("Portfolio heat: %.1f%%", heat.get("heat_pct", 0))
    except Exception as e:
        ctx.errors.append(f"portfolio_heat: {e}")
        logger.warning("Portfolio heat check failed: %s", e)


async def detect_regime(ctx: PipelineContext) -> None:
    """Detect current market regime via HMM."""
    try:
        from hmm_regime import detect_regime as _detect
        regime = await run_sync(_detect)
        ctx.regime = regime.get("regime", "neutral")
        ctx.regime_confidence = regime.get("confidence", 0)
        logger.info("Regime: %s (%.0f%% confidence)",
                    ctx.regime, ctx.regime_confidence * 100)
    except Exception as e:
        ctx.regime = "neutral"
        ctx.errors.append(f"regime: {e}")
        logger.warning("Regime detection failed: %s", e)


async def check_session_quality(ctx: PipelineContext) -> None:
    """Determine current session quality for entry timing."""
    try:
        from smart_entry import get_session_quality
        session = await run_sync(get_session_quality)
        ctx.session = session
        logger.info("Session: %s (quality: %.0f%%)",
                    session.get("label", "?"), session.get("quality", 0) * 100)
    except Exception as e:
        ctx.errors.append(f"session: {e}")
        logger.warning("Session quality check failed: %s", e)


async def run_preflight(ctx: PipelineContext) -> None:
    """Run all preflight checks concurrently."""
    logger.info("=" * 60)
    logger.info("OpenClaw v3.0 — Pre-flight Checks")
    logger.info("=" * 60)

    await asyncio.gather(
        check_circuit_breaker(ctx),
        check_portfolio_heat(ctx),
        detect_regime(ctx),
        check_session_quality(ctx),
    )

    logger.info("Pre-flight complete: %s | Regime=%s | Heat=%.1f%%",
                "PASSED" if ctx.preflight_passed else "FAILED",
                ctx.regime,
                ctx.portfolio_heat.get("heat_pct", 0))


# ══════════════════════════════════════════════════════════════
# STAGE 2: SCAN & SCORE (parallel data fetch → serial scoring)
# ══════════════════════════════════════════════════════════════

async def run_daily_scanner(ctx: PipelineContext) -> list:
    """Execute the full daily scanner pipeline."""
    try:
        from daily_scanner import DailyScanner
        scanner = DailyScanner()
        results = await run_sync(scanner.run_full_scan)

        if isinstance(results, dict):
            ctx.bridge_result = results.get("bridge_result", {})
            return results.get("watchlist", [])
        return results if isinstance(results, list) else []
    except Exception as e:
        ctx.errors.append(f"daily_scanner: {e}")
        logger.error("Daily scanner failed: %s", e)
        return []


async def enhance_candidates(ctx: PipelineContext, raw: list) -> None:
    """Apply smart entry scoring and position sizing to candidates."""
    try:
        from smart_entry import score_entry_quality, calculate_limit_price
        from position_sizer import calculate_position_size

        session = ctx.session

        for candidate in raw:
            ticker = candidate.get("ticker", candidate.get("symbol", ""))
            if not ticker:
                continue

            technicals = {
                "price": candidate.get("price", 0),
                "rsi": candidate.get("rsi", 50),
                "vwap": candidate.get("vwap", 0),
                "atr": candidate.get("atr", 0),
                "sma_20": candidate.get("sma_20", 0),
                "sma_200": candidate.get("sma_200", 0),
                "ema_50": candidate.get("ema_50", 0),
                "adx": candidate.get("adx", 20),
                "volume_ratio": candidate.get("volume_ratio", 1.0),
            }

            entry = score_entry_quality(technicals, session)
            pricing = calculate_limit_price(
                technicals["price"], technicals["atr"], technicals["vwap"]
            )

            try:
                sizing = calculate_position_size(
                    ticker=ticker, price=technicals["price"],
                    atr=technicals["atr"],
                    composite_score=candidate.get("composite_score", 50),
                )
            except Exception:
                sizing = {"shares": 0, "risk_dollars": 0}

            candidate.update({
                "entry_score": entry.get("entry_score", 0),
                "entry_grade": entry.get("entry_grade", "C"),
                "recommendation": entry.get("recommendation", "skip"),
                "limit_price": pricing.get("limit_price", 0),
                "stop_loss": pricing.get("stop_loss", 0),
                "take_profit": pricing.get("take_profit_1", 0),
                "reward_risk": pricing.get("reward_risk_ratio", 0),
                "position_shares": sizing.get("shares", 0),
                "regime": ctx.regime,
                "session": ctx.session.get("session", "unknown"),
            })
            ctx.candidates.append(candidate)

        # Sort by entry score
        ctx.candidates.sort(key=lambda x: x.get("entry_score", 0), reverse=True)
        ctx.tradeable = [c for c in ctx.candidates if c.get("recommendation") != "skip"]

        logger.info("Enhanced: %d scored, %d tradeable",
                    len(ctx.candidates), len(ctx.tradeable))

    except Exception as e:
        ctx.errors.append(f"enhancement: {e}")
        logger.error("Candidate enhancement failed: %s", e)
        ctx.candidates = raw
        ctx.tradeable = raw


async def run_risk_gating(ctx: PipelineContext) -> None:
    """Pass tradeable candidates through the RiskGovernor."""
    try:
        from risk_governor import approve_order
        gated = []
        for c in ctx.tradeable:
            ticker = c.get("ticker", c.get("symbol", ""))
            decision = approve_order(
                ticker=ticker,
                side="buy",
                shares=c.get("position_shares", 0),
                price=c.get("limit_price", c.get("price", 0)),
                stop_loss=c.get("stop_loss", 0),
                composite_score=c.get("composite_score", 0),
                sector=c.get("sector", ""),
                regime=ctx.regime,
                setup_type=c.get("setup_type", ""),
            )
            c["risk_approved"] = decision.approved
            c["risk_reason"] = decision.reason
            c["approved_shares"] = decision.approved_shares
            if decision.approved:
                gated.append(c)
        ctx.tradeable = gated
        logger.info("Risk gating: %d candidates passed", len(gated))
    except ImportError:
        logger.warning("risk_governor not available — skipping gating")
    except Exception as e:
        ctx.errors.append(f"risk_gating: {e}")
        logger.error("Risk gating failed: %s", e)


async def run_scan_pipeline(ctx: PipelineContext) -> None:
    """Full scan → score → gate pipeline."""
    logger.info("=" * 60)
    logger.info("OpenClaw v3.0 — Scan & Score Pipeline")
    logger.info("=" * 60)

    raw_candidates = await run_daily_scanner(ctx)
    logger.info("Scanner returned %d raw candidates", len(raw_candidates))

    await enhance_candidates(ctx, raw_candidates)
    await run_risk_gating(ctx)


# ══════════════════════════════════════════════════════════════
# STAGE 3: POSITION MONITORING
# ══════════════════════════════════════════════════════════════

async def monitor_positions(ctx: PipelineContext) -> None:
    """Monitor open positions with trailing stops."""
    logger.info("=" * 60)
    logger.info("OpenClaw v3.0 — Position Monitor")
    logger.info("=" * 60)
    try:
        from position_manager import PositionManager
        pm = PositionManager()
        summary = await run_sync(pm.get_portfolio_summary)
        ctx.positions = summary
        logger.info("Open: %d | P&L: $%+.2f | Value: $%,.2f",
                    summary.get("open_positions", 0),
                    summary.get("total_pnl", 0),
                    summary.get("total_value", 0))
    except Exception as e:
        ctx.errors.append(f"positions: {e}")
        logger.error("Position monitoring failed: %s", e)


# ══════════════════════════════════════════════════════════════
# STAGE 4: REPORTING
# ══════════════════════════════════════════════════════════════

async def generate_report(days: int = None) -> str:
    """Generate full performance report."""
    try:
        from performance_tracker import (
            format_performance_report, format_regime_report, format_grade_report,
        )
        parts = [
            await run_sync(format_performance_report, days),
            "",
            await run_sync(format_regime_report),
            "",
            await run_sync(format_grade_report),
        ]
        return "\n".join(parts)
    except Exception as e:
        return f"Report generation failed: {e}"


async def post_summary_to_slack(ctx: PipelineContext) -> None:
    """Post pipeline summary to Slack."""
    try:
        from config import OC_TRADE_DESK_CHANNEL, SLACK_BOT_TOKEN
        if not SLACK_BOT_TOKEN or not OC_TRADE_DESK_CHANNEL:
            return

        from slack_sdk.web.async_client import AsyncWebClient
        client = AsyncWebClient(token=SLACK_BOT_TOKEN)

        summary = ctx.to_dict()
        blocks = [
            {"type": "header", "text": {"type": "plain_text",
             "text": f"🦀 OpenClaw v3.0 Pipeline Complete"}},
            {"type": "section", "text": {"type": "mrkdwn", "text":
             f"*Regime:* {ctx.regime} ({ctx.regime_confidence:.0%})\n"
             f"*Candidates:* {len(ctx.candidates)} scored → "
             f"{len(ctx.tradeable)} tradeable\n"
             f"*Positions:* {ctx.positions.get('open_positions', 0)}\n"
             f"*Elapsed:* {ctx.elapsed:.1f}s"}},
        ]

        if ctx.tradeable:
            top = ctx.tradeable[:5]
            lines = [f"• *{c.get('ticker', '?')}* — "
                     f"Grade {c.get('entry_grade', '?')} | "
                     f"Score {c.get('entry_score', 0):.0f} | "
                     f"${c.get('limit_price', 0):.2f}"
                     for c in top]
            blocks.append({"type": "section", "text": {"type": "mrkdwn",
                          "text": "\n".join(lines)}})

        await client.chat_postMessage(
            channel=OC_TRADE_DESK_CHANNEL, blocks=blocks,
            text=f"Pipeline complete: {len(ctx.tradeable)} tradeable"
        )
    except Exception as e:
        logger.debug("Slack post skipped: %s", e)


# ══════════════════════════════════════════════════════════════
# FULL PIPELINE ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

async def run_full_pipeline() -> dict:
    """Async orchestrator for the complete trading pipeline."""
    ctx = PipelineContext()

    logger.info("#" * 60)
    logger.info("OpenClaw v3.0 Pipeline Started: %s",
                ctx.start_time.strftime("%Y-%m-%d %H:%M:%S ET"))
    logger.info("#" * 60)

    # Stage 1: Pre-flight (all checks in parallel)
    await run_preflight(ctx)

    # Early exit on critical circuit breaker
    if not ctx.preflight_passed:
        action = ctx.circuit_breaker.get("action", "")
        if action == "HALT_ALL_TRADING":
            logger.warning("HALT — Circuit breaker CRITICAL")
            return {"status": "HALTED", "reason": "circuit_breaker_critical"}
        elif action == "HALT_NEW_ENTRIES":
            logger.warning("Monitor-only mode — no new entries")
            await monitor_positions(ctx)
            return {"status": "MONITOR_ONLY", **ctx.to_dict()}

    # Stage 2 & 3: Scan + Position Monitor in parallel
    await asyncio.gather(
        run_scan_pipeline(ctx),
        monitor_positions(ctx),
    )

    # Stage 4: Post summary
    await post_summary_to_slack(ctx)

    # Final summary
    summary = ctx.to_dict()
    logger.info("#" * 60)
    logger.info("Pipeline Complete in %.1fs", ctx.elapsed)
    logger.info("  Regime: %s | Candidates: %d → %d tradeable | "
                "Positions: %d",
                ctx.regime, len(ctx.candidates), len(ctx.tradeable),
                ctx.positions.get("open_positions", 0))
    logger.info("#" * 60)

    return summary


# ══════════════════════════════════════════════════════════════
# STREAMING MODE (continuous event loop)
# ══════════════════════════════════════════════════════════════

async def run_streaming_mode() -> None:
    """Launch the streaming engine as an async task."""
    logger.info("Starting streaming mode...")
    try:
        from streaming_engine import StreamingEngine
        engine = StreamingEngine()
        await run_sync(engine.start)
    except Exception as e:
        logger.error("Streaming engine failed: %s", e)


# ══════════════════════════════════════════════════════════════
# ENTRYPOINT
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="OpenClaw v3.0 Async Pipeline")
    parser.add_argument("--positions-only", action="store_true",
                        help="Monitor positions only")
    parser.add_argument("--report", action="store_true",
                        help="Generate performance report")
    parser.add_argument("--report-days", type=int, default=None,
                        help="Report lookback period in days")
    parser.add_argument("--circuit-check", action="store_true",
                        help="Circuit breaker check only")
    parser.add_argument("--preflight", action="store_true",
                        help="Run preflight checks only")
    parser.add_argument("--stream", action="store_true",
                        help="Launch streaming engine")
    parser.add_argument("--dashboard", action="store_true",
                        help="Start live dashboard")
    args = parser.parse_args()

    if args.positions_only:
        ctx = PipelineContext()
        asyncio.run(monitor_positions(ctx))
    elif args.report:
        report = asyncio.run(generate_report(args.report_days))
        print(report)
    elif args.circuit_check:
        ctx = PipelineContext()
        asyncio.run(check_circuit_breaker(ctx))
        print(f"Circuit breaker: {ctx.circuit_breaker}")
    elif args.preflight:
        ctx = PipelineContext()
        asyncio.run(run_preflight(ctx))
    elif args.stream:
        asyncio.run(run_streaming_mode())
    elif args.dashboard:
        from live_dashboard import create_app
        app = create_app()
        app.run(host="0.0.0.0", port=5001, debug=False)
    else:
        result = asyncio.run(run_full_pipeline())
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
