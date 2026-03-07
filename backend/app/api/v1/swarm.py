"""Swarm & Knowledge Ingestion API routes.

Provides endpoints for:
  - Feeding data into the system (YouTube, news, URLs, text, symbols)
  - Managing the autonomous scout service (watchlist, config)
  - Monitoring swarm status and results
  - Managing Discord channel monitoring
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.core.security import require_auth

router = APIRouter()


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------
class IngestYouTubeRequest(BaseModel):
    url: str = ""
    transcript: str = ""
    title: str = ""
    channel: str = ""

class IngestNewsRequest(BaseModel):
    url: str = ""
    text: str = ""
    title: str = ""
    source_name: str = ""

class IngestTextRequest(BaseModel):
    text: str
    idea_type: str = "trade_idea"  # trade_idea, chart_analysis, research, note
    symbols: Optional[List[str]] = None

class IngestURLRequest(BaseModel):
    url: str
    hint: str = ""

class IngestSymbolsRequest(BaseModel):
    symbols: List[str]
    reason: str = "User requested analysis"

class WatchlistRequest(BaseModel):
    symbols: List[str]

class AddChannelRequest(BaseModel):
    channel_id: int
    name: str
    source: str = "custom"
    type: str = "trade_idea"

class ScoutConfigRequest(BaseModel):
    flow_scan_interval: Optional[int] = None
    screener_scan_interval: Optional[int] = None
    watchlist_scan_interval: Optional[int] = None
    backtest_scan_interval: Optional[int] = None
    max_discoveries_per_scan: Optional[int] = None
    enabled_scouts: Optional[List[str]] = None


# ------------------------------------------------------------------
# Knowledge Ingestion endpoints
# ------------------------------------------------------------------
@router.post("/ingest/youtube", dependencies=[Depends(require_auth)])
async def ingest_youtube(req: IngestYouTubeRequest):
    """Ingest a YouTube video transcript into the knowledge base.

    Provide either a URL (will try to fetch transcript automatically)
    or paste the transcript text directly. Extracted symbols will
    trigger a swarm analysis automatically.
    """
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_youtube(
        url=req.url, transcript=req.transcript,
        title=req.title, channel=req.channel,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ingest/news", dependencies=[Depends(require_auth)])
async def ingest_news(req: IngestNewsRequest):
    """Ingest a news article into the knowledge base.

    Provide a URL to scrape or paste the article text directly.
    """
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_news(
        url=req.url, text=req.text,
        title=req.title, source_name=req.source_name,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ingest/text", dependencies=[Depends(require_auth)])
async def ingest_text(req: IngestTextRequest):
    """Ingest free-text: trade ideas, chart analysis, research notes.

    The system will extract symbols, direction, and concepts automatically.
    """
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_text(
        text=req.text, idea_type=req.idea_type, symbols=req.symbols,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ingest/url", dependencies=[Depends(require_auth)])
async def ingest_url(req: IngestURLRequest):
    """Scrape a URL and ingest the content.

    Works with any URL: news sites, blog posts, research reports.
    YouTube URLs will be handled specially (transcript extraction).
    """
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_url(url=req.url, hint=req.hint)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/ingest/symbols", dependencies=[Depends(require_auth)])
async def ingest_symbols(req: IngestSymbolsRequest):
    """Queue multiple symbols for swarm analysis.

    The simplest way to say 'analyze these tickers.'
    Each symbol gets its own swarm: data ingestion + council + backtest.
    """
    from app.services.knowledge_ingest import knowledge_ingest
    result = await knowledge_ingest.ingest_symbols(
        symbols=req.symbols, reason=req.reason,
    )
    return result


@router.get("/ingest/feed")
async def get_knowledge_feed(limit: int = 50, type_filter: str = None):
    """Get recent knowledge feed entries."""
    from app.services.knowledge_ingest import knowledge_ingest
    return {
        "entries": knowledge_ingest.get_knowledge_feed(limit=limit, type_filter=type_filter),
        "stats": knowledge_ingest.get_stats(),
    }


# ------------------------------------------------------------------
# Swarm management endpoints
# ------------------------------------------------------------------
@router.get("/swarm/status")
async def swarm_status():
    """Get swarm spawner status: active swarms, queue depth, stats."""
    from app.services.swarm_spawner import get_swarm_spawner
    return get_swarm_spawner().get_status()


@router.get("/swarm/results")
async def swarm_results(limit: int = 20, source: str = None):
    """Get recent swarm analysis results."""
    from app.services.swarm_spawner import get_swarm_spawner
    return {
        "results": get_swarm_spawner().get_results(limit=limit, source=source),
    }


@router.get("/swarm/result/{idea_id}")
async def swarm_result(idea_id: str):
    """Get a specific swarm result by idea ID."""
    from app.services.swarm_spawner import get_swarm_spawner
    result = get_swarm_spawner().get_result(idea_id)
    if not result:
        raise HTTPException(status_code=404, detail="Swarm result not found")
    return result


# ------------------------------------------------------------------
# Scout management endpoints
# ------------------------------------------------------------------
@router.get("/scout/status")
async def scout_status():
    """Get autonomous scout service status."""
    from app.services.autonomous_scout import get_scout_service
    return get_scout_service().get_status()


@router.post("/scout/watchlist", dependencies=[Depends(require_auth)])
async def set_watchlist(req: WatchlistRequest):
    """Set the scout watchlist (replaces existing)."""
    from app.services.autonomous_scout import get_scout_service
    get_scout_service().set_watchlist(req.symbols)
    return {"status": "ok", "watchlist": get_scout_service()._watchlist}


@router.post("/scout/watchlist/add", dependencies=[Depends(require_auth)])
async def add_to_watchlist(req: WatchlistRequest):
    """Add symbols to the scout watchlist."""
    from app.services.autonomous_scout import get_scout_service
    get_scout_service().add_to_watchlist(req.symbols)
    return {"status": "ok", "watchlist": get_scout_service()._watchlist}


@router.post("/scout/watchlist/remove", dependencies=[Depends(require_auth)])
async def remove_from_watchlist(req: WatchlistRequest):
    """Remove symbols from the scout watchlist."""
    from app.services.autonomous_scout import get_scout_service
    get_scout_service().remove_from_watchlist(req.symbols)
    return {"status": "ok", "watchlist": get_scout_service()._watchlist}


@router.post("/scout/config", dependencies=[Depends(require_auth)])
async def update_scout_config(req: ScoutConfigRequest):
    """Update scout configuration (scan intervals, enabled scouts)."""
    from app.services.autonomous_scout import get_scout_service
    scout = get_scout_service()
    if req.flow_scan_interval is not None:
        scout.config["flow_scan_interval"] = req.flow_scan_interval
    if req.screener_scan_interval is not None:
        scout.config["screener_scan_interval"] = req.screener_scan_interval
    if req.watchlist_scan_interval is not None:
        scout.config["watchlist_scan_interval"] = req.watchlist_scan_interval
    if req.backtest_scan_interval is not None:
        scout.config["backtest_scan_interval"] = req.backtest_scan_interval
    if req.max_discoveries_per_scan is not None:
        scout.config["max_discoveries_per_scan"] = req.max_discoveries_per_scan
    if req.enabled_scouts is not None:
        scout.config["enabled_scouts"] = req.enabled_scouts
    return {"status": "ok", "config": scout.config}


@router.post("/scout/reset", dependencies=[Depends(require_auth)])
async def reset_scout_discoveries():
    """Reset daily discoveries so scouts can re-scan symbols."""
    from app.services.autonomous_scout import get_scout_service
    get_scout_service().reset_daily_discoveries()
    return {"status": "ok", "message": "Daily discoveries reset"}


# ------------------------------------------------------------------
# Discord channel management
# ------------------------------------------------------------------
@router.get("/discord/status")
async def discord_status():
    """Get Discord swarm bridge status."""
    from app.services.discord_swarm_bridge import get_discord_bridge
    return get_discord_bridge().get_status()


@router.get("/discord/channels")
async def discord_channels():
    """List all monitored Discord channels."""
    from app.services.discord_swarm_bridge import get_discord_bridge
    return {"channels": get_discord_bridge().list_channels()}


@router.post("/discord/channels", dependencies=[Depends(require_auth)])
async def add_discord_channel(req: AddChannelRequest):
    """Add a Discord channel to monitor.

    You'll need the channel ID (right-click channel in Discord -> Copy ID).
    """
    from app.services.discord_swarm_bridge import get_discord_bridge
    get_discord_bridge().add_channel(
        channel_id=req.channel_id, name=req.name,
        source=req.source, msg_type=req.type,
    )
    return {"status": "ok", "channels": get_discord_bridge().list_channels()}


@router.delete("/discord/channels/{channel_id}", dependencies=[Depends(require_auth)])
async def remove_discord_channel(channel_id: int):
    """Remove a Discord channel from monitoring."""
    from app.services.discord_swarm_bridge import get_discord_bridge
    get_discord_bridge().remove_channel(channel_id)
    return {"status": "ok", "channels": get_discord_bridge().list_channels()}


class InjectEventRequest(BaseModel):
    headline: str
    description: str = ""
    event_type: str = ""  # military_conflict, financial_crisis, etc.
    severity: str = "high"  # critical, high, medium, low


# ------------------------------------------------------------------
# Geopolitical Radar endpoints
# ------------------------------------------------------------------
@router.get("/radar/status")
async def radar_status():
    """Get geopolitical radar status: alert level, active events, scan stats."""
    from app.services.geopolitical_radar import get_geopolitical_radar
    return get_geopolitical_radar().get_status()


@router.get("/radar/playbook")
async def radar_playbook(event_type: str = None):
    """Get the macro event playbook — what trades execute for each event type.

    Shows exactly what happens if war breaks out, a bank fails, etc.
    """
    from app.services.geopolitical_radar import get_geopolitical_radar
    return {"playbook": get_geopolitical_radar().get_playbook(event_type)}


@router.post("/radar/inject", dependencies=[Depends(require_auth)])
async def inject_event(req: InjectEventRequest):
    """Manually inject a macro event to test the system's response.

    Example: inject a 'military_conflict' event to see which swarms spawn.
    """
    from app.services.geopolitical_radar import get_geopolitical_radar, MacroEvent
    radar = get_geopolitical_radar()
    event = MacroEvent(
        event_type=req.event_type or "unknown",
        severity=req.severity,
        headline=req.headline,
        description=req.description,
        source="manual_injection",
    )
    radar.inject_event(event)
    return {
        "status": "injected",
        "event": event.to_dict(),
        "message": "Event injected — swarms will spawn for playbook instruments",
    }


class SetExpectedMoveLevelsRequest(BaseModel):
    symbol: str
    upper: float
    lower: float
    source: str = "fom_discord"


# ------------------------------------------------------------------
# Correlation Radar endpoints
# ------------------------------------------------------------------
@router.get("/correlations/status")
async def correlation_status():
    """Get correlation radar status: active breaks, rotation signals, reversion signals."""
    from app.services.correlation_radar import get_correlation_radar
    return get_correlation_radar().get_status()


@router.get("/correlations/matrix")
async def correlation_matrix():
    """Get the current cross-asset correlation matrix."""
    from app.services.correlation_radar import get_correlation_radar
    return get_correlation_radar().get_correlation_matrix()


@router.get("/correlations/rotations")
async def rotation_signals(limit: int = 20):
    """Get recent sector rotation signals."""
    from app.services.correlation_radar import get_correlation_radar
    return {"rotations": get_correlation_radar().get_rotation_signals(limit)}


@router.get("/correlations/reversions")
async def reversion_signals(limit: int = 20):
    """Get mean reversion signals (overextended symbols likely to snap back)."""
    from app.services.correlation_radar import get_correlation_radar
    return {"reversions": get_correlation_radar().get_reversion_signals(limit)}


# ------------------------------------------------------------------
# Pattern Library endpoints
# ------------------------------------------------------------------
@router.get("/patterns/status")
async def pattern_library_status():
    """Get pattern library status: total patterns, validated, active."""
    from app.services.pattern_library import get_pattern_library
    return get_pattern_library().get_status()


@router.get("/patterns/list")
async def list_patterns(pattern_type: str = None):
    """List all patterns with their backtest statistics.

    Filter by type: reversal, rotation, momentum, expected_move, cycle
    """
    from app.services.pattern_library import get_pattern_library
    return {"patterns": get_pattern_library().get_patterns(pattern_type)}


@router.get("/patterns/{pattern_id}")
async def get_pattern(pattern_id: str):
    """Get details of a specific pattern including backtest stats."""
    from app.services.pattern_library import get_pattern_library
    p = get_pattern_library().get_pattern(pattern_id)
    if not p:
        raise HTTPException(status_code=404, detail="Pattern not found")
    return p


# ------------------------------------------------------------------
# Expected Move Service endpoints
# ------------------------------------------------------------------
@router.get("/expected-moves/levels")
async def expected_move_levels(symbol: str = None):
    """Get expected move levels for tracked symbols.

    Shows upper/lower boundaries where reversals are statistically likely.
    """
    from app.services.expected_move_service import get_expected_move_service
    return {"levels": get_expected_move_service().get_levels(symbol)}


@router.get("/expected-moves/reversals")
async def expected_move_reversals():
    """Get symbols currently at expected move reversal zones."""
    from app.services.expected_move_service import get_expected_move_service
    return {"reversal_zones": get_expected_move_service().get_reversal_zones()}


@router.post("/expected-moves/fom-levels", dependencies=[Depends(require_auth)])
async def set_fom_levels(req: SetExpectedMoveLevelsRequest):
    """Set expected move levels from FOM Discord or manual input.

    Use this to override calculated levels with real options-derived data
    from FOM's expected move analysis.
    """
    from app.services.expected_move_service import get_expected_move_service
    get_expected_move_service().set_fom_levels(req.symbol, req.upper, req.lower, req.source)
    return {
        "status": "ok",
        "symbol": req.symbol.upper(),
        "upper": req.upper,
        "lower": req.lower,
    }


@router.get("/expected-moves/status")
async def expected_move_status():
    """Get expected move service status."""
    from app.services.expected_move_service import get_expected_move_service
    return get_expected_move_service().get_status()


# ------------------------------------------------------------------
# Combined system status
# ------------------------------------------------------------------
@router.get("/intelligence/status")
async def intelligence_status():
    """Get combined status of ALL intelligence systems."""
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    from app.services.swarm_spawner import get_swarm_spawner
    from app.services.autonomous_scout import get_scout_service
    from app.services.discord_swarm_bridge import get_discord_bridge
    from app.services.knowledge_ingest import knowledge_ingest
    from app.services.geopolitical_radar import get_geopolitical_radar
    from app.services.correlation_radar import get_correlation_radar
    from app.services.pattern_library import get_pattern_library
    from app.services.expected_move_service import get_expected_move_service

    from app.services.turbo_scanner import get_turbo_scanner
    from app.services.hyper_swarm import get_hyper_swarm
    from app.services.news_aggregator import get_news_aggregator
    from app.services.market_wide_sweep import get_market_sweep

    def _safe_status(name, fn):
        try:
            return fn()
        except Exception as e:
            _logger.warning("intelligence_status: %s failed: %s", name, e)
            return {"error": str(e)}

    return {
        "swarm": _safe_status("swarm", get_swarm_spawner().get_status),
        "hyper_swarm": _safe_status("hyper_swarm", get_hyper_swarm().get_status),
        "turbo_scanner": _safe_status("turbo_scanner", get_turbo_scanner().get_status),
        "news_aggregator": _safe_status("news_aggregator", get_news_aggregator().get_status),
        "market_sweep": _safe_status("market_sweep", get_market_sweep().get_status),
        "scout": _safe_status("scout", get_scout_service().get_status),
        "discord": _safe_status("discord", get_discord_bridge().get_status),
        "radar": _safe_status("radar", get_geopolitical_radar().get_status),
        "correlations": _safe_status("correlations", get_correlation_radar().get_status),
        "patterns": _safe_status("patterns", get_pattern_library().get_status),
        "expected_moves": _safe_status("expected_moves", get_expected_move_service().get_status),
        "ingestion": _safe_status("ingestion", knowledge_ingest.get_stats),
    }


# ------------------------------------------------------------------
# TurboScanner endpoints
# ------------------------------------------------------------------
@router.get("/turbo/status")
async def turbo_scanner_status():
    """Get TurboScanner status: scan rate, signals found, volatile mode."""
    from app.services.turbo_scanner import get_turbo_scanner
    try:
        return get_turbo_scanner().get_status()
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).error("turbo/status error: %s", e, exc_info=True)
        return {"error": str(e), "running": False}


@router.get("/turbo/signals")
async def turbo_signals(signal_type: str = None, limit: int = 50):
    """Get recent signals from TurboScanner.

    Filter by type: technical_breakout, volume_spike, momentum_surge,
    rsi_extreme, macd_cross, sector_divergence, vix_regime,
    unusual_flow, mean_reversion
    """
    from app.services.turbo_scanner import get_turbo_scanner
    try:
        return {"signals": get_turbo_scanner().get_signals(signal_type, limit)}
    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).error("turbo/signals error: %s", e, exc_info=True)
        return {"signals": [], "error": str(e)}


@router.post("/turbo/reset-daily", dependencies=[Depends(require_auth)])
async def turbo_reset():
    """Reset daily dedup set (call at market open to allow re-scanning)."""
    from app.services.turbo_scanner import get_turbo_scanner
    get_turbo_scanner().reset_daily()
    return {"status": "ok", "message": "Daily signal dedup cleared"}


# ------------------------------------------------------------------
# HyperSwarm endpoints
# ------------------------------------------------------------------
@router.get("/hyper/status")
async def hyper_swarm_status():
    """Get HyperSwarm status: queue depth, workers, score distribution."""
    from app.services.hyper_swarm import get_hyper_swarm
    return get_hyper_swarm().get_status()


@router.get("/hyper/results")
async def hyper_results(limit: int = 50, min_score: int = 0):
    """Get micro-swarm analysis results. Filter by minimum score (0-100)."""
    from app.services.hyper_swarm import get_hyper_swarm
    return {"results": get_hyper_swarm().get_results(limit, min_score)}


@router.get("/hyper/escalations")
async def hyper_escalations(limit: int = 20):
    """Get signals escalated to full council by HyperSwarm (score >= 65)."""
    from app.services.hyper_swarm import get_hyper_swarm
    return {"escalations": get_hyper_swarm().get_escalations(limit)}


# ------------------------------------------------------------------
# NewsAggregator endpoints
# ------------------------------------------------------------------
@router.get("/news/status")
async def news_aggregator_status():
    """Get NewsAggregator status: feeds active, items processed, sentiment breakdown."""
    from app.services.news_aggregator import get_news_aggregator
    return get_news_aggregator().get_status()


@router.get("/news/feed")
async def news_feed(source: str = None, sentiment: str = None, limit: int = 50):
    """Get aggregated news feed. Filter by source or sentiment (bullish/bearish/neutral)."""
    from app.services.news_aggregator import get_news_aggregator
    return {"news": get_news_aggregator().get_news(source, sentiment, limit)}


# ------------------------------------------------------------------
# MarketWideSweep endpoints
# ------------------------------------------------------------------
@router.get("/sweep/status")
async def market_sweep_status():
    """Get MarketWideSweep status: universe size, screens run, hits found."""
    from app.services.market_wide_sweep import get_market_sweep
    return get_market_sweep().get_status()


@router.get("/sweep/screens")
async def all_screens():
    """Get results from all market-wide screens."""
    from app.services.market_wide_sweep import get_market_sweep
    return {"screens": get_market_sweep().get_all_screens()}


@router.get("/sweep/screen/{screen_name}")
async def get_screen(screen_name: str):
    """Get results from a specific screen.

    Available: momentum_leaders, volume_anomalies, rsi_extremes,
    bollinger_squeeze, sma_crosses, new_highs_lows, mean_reversion,
    institutional_accumulation, sector_strength, consecutive_moves
    """
    from app.services.market_wide_sweep import get_market_sweep
    result = get_market_sweep().get_screen(screen_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Screen '{screen_name}' not found or not yet run")
    return result


# ------------------------------------------------------------------
# Outcome Tracker (P0 — feedback loop)
# ------------------------------------------------------------------

@router.get("/outcomes/status")
async def outcome_tracker_status():
    """Get OutcomeTracker status: win rate, PnL, Kelly params, feedback loop health."""
    from app.services.outcome_tracker import get_outcome_tracker
    return get_outcome_tracker().get_status()

@router.get("/outcomes/kelly")
async def outcome_kelly_params():
    """Get calibrated Kelly parameters derived from real trade outcomes."""
    from app.services.outcome_tracker import get_outcome_tracker
    return get_outcome_tracker().get_kelly_params()

@router.get("/outcomes/open")
async def outcome_open_positions():
    """Get all positions currently being tracked for outcome resolution."""
    from app.services.outcome_tracker import get_outcome_tracker
    return get_outcome_tracker().get_open_positions()

@router.get("/outcomes/closed")
async def outcome_closed_positions(limit: int = 50):
    """Get recently closed positions with PnL and R-multiple."""
    from app.services.outcome_tracker import get_outcome_tracker
    return get_outcome_tracker().get_closed_positions(limit=limit)


# ------------------------------------------------------------------
# Position Manager (P2 — automated exits)
# ------------------------------------------------------------------

@router.get("/positions/managed")
async def managed_positions_status():
    """Get PositionManager status: active positions, trailing stops, exit stats."""
    from app.services.position_manager import get_position_manager
    return get_position_manager().get_status()


# ------------------------------------------------------------------
# ML Scorer (P1 — live model status)
# ------------------------------------------------------------------

@router.get("/ml/scorer/status")
async def ml_scorer_status():
    """Get ML live scorer status: model loaded, predictions made, accuracy."""
    from app.services.ml_scorer import get_ml_scorer
    return get_ml_scorer().get_status()

@router.post("/ml/scorer/reload", dependencies=[Depends(require_auth)])
async def ml_scorer_reload():
    """Reload the ML model (e.g., after retraining)."""
    from app.services.ml_scorer import get_ml_scorer
    loaded = get_ml_scorer().reload()
    return {"reloaded": loaded, "status": get_ml_scorer().get_status()}


# ------------------------------------------------------------------
# Unified Profit Engine (P3 — adaptive ensemble)
# ------------------------------------------------------------------

@router.get("/unified/status")
async def unified_engine_status():
    """Get UnifiedProfitEngine status: brain weights, accuracy, scores produced."""
    from app.services.unified_profit_engine import get_unified_engine
    return get_unified_engine().get_status()

@router.get("/unified/score/{symbol}")
async def unified_score(symbol: str):
    """Get unified score for a symbol across all brains."""
    from app.services.unified_profit_engine import get_unified_engine
    result = await get_unified_engine().score(symbol.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
    return result
