#!/usr/bin/env python3
"""
API Data Bridge for OpenClaw v1.4
Bridge between OpenClaw API data and Perplexity/Claude AI tasks.
Exports structured scanner results to GitHub Gist JSON so
Elite v2 Agent Command Center can consume real API data.

  v1.1: Added fom_expected_moves to Gist payload so Perplexity Tasks
        can read today's expected move levels and update TradingView.

  v1.2: Added local LLM (Ollama) + Perplexity hybrid analysis integration.
        Scan summaries and candidate analysis via llm_client.py.

  v1.3: Added memory intelligence (memory_v3) and sector_rankings to Gist
        payload so Elite v2 Agent Command Center can display memory IQ,
        agent leaderboard, recall data, and sector rotation cards.

  v1.4: Removed Google Sheets dependency (now using proper database).
        Gist JSON + local file are the only export targets.
        Elite v2 backend reads Gist via openclaw_bridge_service.py.

See AI_BRIDGE_BLUEPRINT.md for full architecture docs.
"""
import os
import json
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

# Bridge config
GIST_TOKEN = os.getenv("GIST_TOKEN")
BRIDGE_GIST_ID = os.getenv("BRIDGE_GIST_ID")
AI_BRIDGE_ENABLED = os.getenv("AI_BRIDGE_ENABLED", "True").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Optional imports for memory intelligence + sector rotation
# ---------------------------------------------------------------------------
try:
  from memory_v3 import trade_memory
  HAS_MEMORY_V3 = True
except ImportError:
  trade_memory = None
  HAS_MEMORY_V3 = False

try:
  from sector_rotation import get_sector_rankings as _get_sector_rankings
  HAS_SECTOR_ROTATION = True
except ImportError:
  _get_sector_rankings = None
  HAS_SECTOR_ROTATION = False

def export_scan_for_ai(scan_results):
  """Format OpenClaw scan results into AI-consumable payload."""
  if not scan_results:
    return {"error": "No scan results provided"}

  # Extract regime info
  regime_raw = scan_results.get("regime", "UNKNOWN")
  if isinstance(regime_raw, dict):
    regime_state = regime_raw.get("regime", "UNKNOWN")
    regime_data = regime_raw
  else:
    regime_state = str(regime_raw).upper()
    regime_data = {"state": regime_state}

  # Extract macro context
  macro = scan_results.get("macro") or {}

  # Extract FOM expected moves (from daily_scanner Step 18)
  fom_raw = scan_results.get("fom_expected_moves") or {}
  fom_payload = {}
  if fom_raw and fom_raw.get("tv_string"):
    fom_payload = {
      "date": fom_raw.get("date", ""),
      "count": fom_raw.get("count", 0),
      "tv_string": fom_raw.get("tv_string", ""),
      "levels": {},
    }
    # Include per-ticker levels for programmatic use
    for ticker, data in (fom_raw.get("levels") or {}).items():
      fom_payload["levels"][ticker] = {
        "upper_1sig": data.get("upper_1sig", 0),
        "lower_1sig": data.get("lower_1sig", 0),
        "upper_2sig": data.get("upper_2sig", 0),
        "lower_2sig": data.get("lower_2sig", 0),
      }

  # Build AI payload
  ai_payload = {
    "timestamp": datetime.now().isoformat(),
    "scan_date": date.today().isoformat(),
    "regime": {
      "state": regime_state,
      "vix": macro.get("vix"),
      "hmm_confidence": regime_data.get("confidence"),
      "hurst": regime_data.get("hurst"),
    },
    "macro_context": {
      "fear_greed_value": macro.get("fear_greed_value"),
      "fear_greed_label": macro.get("fear_greed_label"),
      "hy_spread": macro.get("hy_spread"),
      "yield_curve": macro.get("yield_curve"),
      "macro_regime": macro.get("regime"),
    },
    "top_candidates": [],
    "watchlist_symbols": [],
    "whale_flow_alerts": [],
    "fom_expected_moves": fom_payload,
    "sector_rankings": [],
    "recalls": {},
  }

  # Process scored results
  scored = scan_results.get("scored_results", [])
  watchlist = scan_results.get("watchlist", [])

  # Build score map from scored results
  score_map = {}
  for r in scored:
    try:
      score_map[r.ticker] = r
    except AttributeError:
      if isinstance(r, dict):
        score_map[r.get("ticker", r.get("symbol", ""))] = r

  # Process watchlist items with their scores
  for item in watchlist:
    ticker = item.get("ticker", "")
    score = item.get("composite_score", 0)
    tier = item.get("score_tier", "NO_DATA")
    pos = item.get("position_size", {})

    candidate = {
      "symbol": ticker,
      "composite_score": score,
      "tier": tier,
      "source": item.get("source", ""),
      "regime_score": item.get("regime_score", 0),
      "trend_score": item.get("trend_score", 0),
      "pullback_score": item.get("pullback_score", 0),
      "momentum_score": item.get("momentum_score", 0),
      "pattern_score": item.get("pattern_score", 0),
      "price": item.get("price", 0),
      "whale_premium": item.get("whale_premium", 0),
      "whale_sentiment": item.get("whale_sentiment", ""),
      "scan_date": item.get("scan_date", ""),
    }

    # Add position sizing if available
    if isinstance(pos, dict):
      candidate["suggested_entry"] = pos.get("entry_price", 0)
      candidate["suggested_stop"] = pos.get("stop_price", 0)
      candidate["position_size_shares"] = pos.get("shares", 0)
      candidate["risk_dollars"] = pos.get("risk_dollars", 0)

    ai_payload["top_candidates"].append(candidate)
    if score >= 50:
      ai_payload["watchlist_symbols"].append(ticker)

  # Process whale flow alerts
  whale_flows = scan_results.get("whale_flow", [])
  for w in whale_flows[:20]:
    if isinstance(w, dict):
      ai_payload["whale_flow_alerts"].append({
        "ticker": w.get("ticker", w.get("symbol", "")),
        "sentiment": w.get("dominant_sentiment", w.get("sentiment", "")),
        "premium": w.get("total_premium", w.get("premium", 0)),
        "volume": w.get("volume", 0),
        "oi_ratio": w.get("oi_ratio", 0),
      })

  # Sort candidates by score
  ai_payload["top_candidates"].sort(
    key=lambda x: x.get("composite_score", 0), reverse=True
  )

  # ---------------------------------------------------------------------------
  # SECTOR RANKINGS (v1.3)
  # ---------------------------------------------------------------------------
  if HAS_SECTOR_ROTATION and _get_sector_rankings:
    try:
      sectors = _get_sector_rankings()
      for s in (sectors or []):
        ai_payload["sector_rankings"].append({
          "sector": s.get("sector", ""),
          "etf": s.get("etf", ""),
          "pct_change": s.get("pct_change", 0),
          "rank": s.get("rank", 0),
          "status": s.get("status", "NEUTRAL"),
          "volume_ratio": s.get("volume_ratio", 1.0),
          "momentum": s.get("status", "NEUTRAL"),
          "score": s.get("pct_change", 0),
        })
      logger.info(f"[BRIDGE] Sector rankings: {len(ai_payload['sector_rankings'])} sectors")
    except Exception as e:
      logger.warning(f"[BRIDGE] Sector rankings failed (non-fatal): {e}")

  # ---------------------------------------------------------------------------
  # MEMORY INTELLIGENCE (v1.3)
  # ---------------------------------------------------------------------------
  if HAS_MEMORY_V3 and trade_memory:
    try:
      # Quality score (Memory IQ)
      quality = trade_memory.get_memory_quality_score()
      # Agent leaderboard
      agents = trade_memory.get_agent_rankings()
      # Overall expectancy
      expectancy = trade_memory.get_decay_weighted_expectancy()
      # Health status
      health = trade_memory.get_health_status() if hasattr(trade_memory, 'get_health_status') else "ok"
      # Regime-partitioned stats
      regime_stats = trade_memory.get_regime_stats()
      # Source weights
      weights = trade_memory.get_source_weights()

      ai_payload["memory"] = {
        "quality_score": quality,
        "agent_rankings": agents[:10] if agents else [],
        "expectancy_summary": expectancy,
        "health": health,
        "regime_stats": regime_stats,
        "source_weights": weights,
      }

      # Build recalls for top candidates (3-stage recall pipeline)
      recalls = {}
      for c in ai_payload["top_candidates"][:10]:
        ticker = c.get("symbol", "")
        if ticker:
          try:
            recall_data = trade_memory.recall(
              ticker,
              score=c.get("composite_score", 50),
              regime=regime_state,
            )
            if recall_data:
              recalls[ticker] = recall_data
          except Exception:
            pass
      ai_payload["recalls"] = recalls

      logger.info(
        f"[BRIDGE] Memory IQ={quality.get('memory_iq', 0)}, "
        f"{len(agents)} agents, {len(recalls)} recalls"
      )
    except Exception as e:
      logger.warning(f"[BRIDGE] Memory intelligence failed (non-fatal): {e}")

  # ---------------------------------------------------------------------------
  # LLM ANALYSIS (v1.2) - Optional Ollama/Perplexity hybrid
  # ---------------------------------------------------------------------------
  try:
    from llm_client import llm_client
    if llm_client and hasattr(llm_client, 'available') and llm_client.available:
      try:
        summary = llm_client.summarize_scan(ai_payload)
        if summary:
          ai_payload["llm_summary"] = summary
        analysis = llm_client.analyze_candidates(ai_payload.get("top_candidates", [])[:5])
        if analysis:
          ai_payload["llm_candidate_analysis"] = analysis
      except Exception as e:
        logger.warning(f"[BRIDGE] LLM analysis failed (non-fatal): {e}")
    else:
      logger.info("[BRIDGE] No LLM backends available, skipping analysis")
  except ImportError:
    logger.debug("[BRIDGE] llm_client not available, skipping LLM analysis")
  except Exception as e:
    logger.warning(f"[BRIDGE] LLM analysis failed (non-fatal): {e}")

  logger.info(
    f"[BRIDGE] Formatted {len(ai_payload['top_candidates'])} candidates, "
    f"{len(ai_payload['whale_flow_alerts'])} whale alerts, "
    f"FOM={'yes' if fom_payload else 'no'} ({fom_payload.get('count', 0)} symbols), "
    f"sectors={len(ai_payload['sector_rankings'])}, "
    f"memory={'yes' if ai_payload.get('memory') else 'no'}"
  )
  return ai_payload

def push_to_gist(ai_payload):
  """Push scan data to a GitHub Gist as JSON (publicly readable URL)."""
  if not GIST_TOKEN or not BRIDGE_GIST_ID:
    logger.warning("[BRIDGE] Gist credentials not configured, skipping")
    return None

  try:
    import requests
    headers = {
      "Authorization": f"token {GIST_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
    }
    data = {
      "files": {
        "openclaw_scan_latest.json": {
          "content": json.dumps(ai_payload, indent=2, default=str)
        }
      }
    }
    resp = requests.patch(
      f"https://api.github.com/gists/{BRIDGE_GIST_ID}",
      headers=headers,
      json=data,
      timeout=15,
    )
    resp.raise_for_status()
    raw_url = resp.json()["files"]["openclaw_scan_latest.json"]["raw_url"]
    logger.info(f"[BRIDGE] Gist updated: {raw_url}")
    return raw_url
  except Exception as e:
    logger.error(f"[BRIDGE] Gist update failed: {e}")
    return None


def save_local_json(ai_payload):
  """Save scan data locally for Claude bot or other tools."""
  try:
    os.makedirs("data", exist_ok=True)
    path = os.path.join("data", "latest_scan.json")
    with open(path, "w") as f:
      json.dump(ai_payload, f, indent=2, default=str)
    logger.info(f"[BRIDGE] Local JSON saved: {path}")
    return path
  except Exception as e:
    logger.error(f"[BRIDGE] Local save failed: {e}")
    return None

def export_and_push(scan_results):
  """Main entry point: format scan results and push to Gist + local JSON.

  v1.4: Removed Google Sheets push. Elite v2 uses proper PostgreSQL database.
  The Gist JSON is consumed by openclaw_bridge_service.py on the Elite v2 backend.
  """
  if not AI_BRIDGE_ENABLED:
    logger.info("[BRIDGE] AI Bridge disabled, skipping export")
    return {"skipped": True}

  # Step 1: Format the payload
  ai_payload = export_scan_for_ai(scan_results)
  if not ai_payload or "error" in ai_payload:
    logger.warning(f"[BRIDGE] Payload formatting failed: {ai_payload}")
    return {"error": "Payload formatting failed"}

  result = {
    "candidates": len(ai_payload.get("top_candidates", [])),
    "fom_symbols": ai_payload.get("fom_expected_moves", {}).get("count", 0),
    "sector_count": len(ai_payload.get("sector_rankings", [])),
    "memory_iq": ai_payload.get("memory", {}).get("quality_score", {}).get("memory_iq", 0) if ai_payload.get("memory") else 0,
    "recall_count": len(ai_payload.get("recalls", {})),
  }

  # Step 2: Push to GitHub Gist (primary export for Elite v2)
  gist_url = push_to_gist(ai_payload)

  # Step 3: Save local JSON backup
  local_path = save_local_json(ai_payload)

  # Step 4: Optional LLM analysis was already added in export_scan_for_ai
  result["llm_backend"] = ai_payload.get("llm_summary") is not None

  logger.info(
    f"[BRIDGE] Export complete: {result['candidates']} candidates, "
    f"gist={'OK' if gist_url else 'SKIP'}, "
    f"local={'OK' if local_path else 'SKIP'}, "
    f"fom={result['fom_symbols']} symbols, "
    f"sectors={result['sector_count']}, "
    f"memory_iq={result['memory_iq']}, "
    f"recalls={result['recall_count']}"
  )

  return result


if __name__ == "__main__":
  # Standalone test: run a scan and bridge it
  logging.basicConfig(level=logging.INFO)
  print("[BRIDGE] Running standalone test...")
  try:
    from daily_scanner import run_daily_scan
    results = run_daily_scan()
    bridge_result = export_and_push(results)
    print(f"[BRIDGE] Result: {json.dumps(bridge_result, indent=2, default=str)}")
  except Exception as e:
    print(f"[BRIDGE] Standalone test failed: {e}")
    print("[BRIDGE] Try running with proper .env configured")
