"""Hypothesis Agent — LLM-powered hypothesis via Brain Service.

GPU Channel 6: Parallel LLM hypothesis generation — fires 4 concurrent
Ollama calls (bullish thesis, bearish thesis, catalyst analysis, risk
assessment) and synthesizes results. Requires OLLAMA_NUM_PARALLEL=4 on PC2.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List

from app.council.agent_config import get_agent_thresholds
from app.council.schemas import AgentVote

logger = logging.getLogger(__name__)

NAME = "hypothesis"


async def evaluate(
    symbol: str, timeframe: str, features: Dict[str, Any], context: Dict[str, Any]
) -> AgentVote:
    """Call brain_client for LLM inference when enabled; otherwise stub."""
    cfg = get_agent_thresholds()

    try:
        from app.services.brain_client import get_brain_client

        client = get_brain_client()
        if not client.enabled:
            # Fallback: try LLM router brainstem tier
            try:
                return await _hypothesis_via_router(symbol, timeframe, features, context, cfg)
            except Exception:
                return AgentVote(
                    agent_name=NAME,
                    direction="hold",
                    confidence=0.1,
                    reasoning="Brain service disabled and LLM router unavailable",
                    weight=cfg["weight_hypothesis"],
                    metadata={"brain_enabled": False, "router_fallback": False},
                )

        feature_json = json.dumps(features.get("features", features), default=str)
        regime = str(features.get("features", {}).get("regime", "unknown"))

        # Load trading directives for current regime
        directives_text = ""
        try:
            from app.council.directives.loader import directive_loader
            directives_text = directive_loader.load(regime)
        except Exception:
            pass

        # Build rich context from blackboard (perceptions + regime + features + directives)
        blackboard = context.get("blackboard")
        if blackboard:
            brain_context = json.dumps({
                "perceptions": blackboard.perceptions,
                "regime": regime,
                "council_decision_id": blackboard.council_decision_id,
                "stage1_votes": context.get("stage1", {}),
                "directives": directives_text[:2000] if directives_text else "",
            }, default=str)
        else:
            brain_context = json.dumps(context, default=str) if context else ""

        result = await client.infer(
            symbol=symbol,
            timeframe=timeframe,
            feature_json=feature_json,
            regime=regime,
            context=brain_context,
        )

        # Map LLM confidence to direction (coerce to float for safety)
        try:
            llm_conf = float(result.get("confidence", 0.5))
        except (ValueError, TypeError):
            llm_conf = 0.5
        risk_flags = result.get("risk_flags", [])

        if "llm_unavailable" in risk_flags or "brain_disabled" in risk_flags:
            return AgentVote(
                agent_name=NAME,
                direction="hold",
                confidence=0.1,
                reasoning=result.get("summary", "LLM unavailable"),
                weight=cfg["weight_hypothesis"],
                metadata={"brain_enabled": True, "error": result.get("error", "")},
            )

        if llm_conf > cfg["llm_buy_confidence_threshold"]:
            direction = "buy"
        elif llm_conf < cfg["llm_sell_confidence_threshold"]:
            direction = "sell"
        else:
            direction = "hold"

        reasoning = result.get("summary", "No summary")
        bullets = result.get("reasoning_bullets", [])
        if bullets:
            reasoning += " | " + "; ".join(bullets[:3])

        return AgentVote(
            agent_name=NAME,
            direction=direction,
            confidence=round(llm_conf, 2),
            reasoning=reasoning,
            weight=cfg["weight_hypothesis"],
            metadata={
                "brain_enabled": True,
                "risk_flags": risk_flags,
            },
        )

    except Exception as e:
        logger.warning("Hypothesis agent error: %s", e)
        return AgentVote(
            agent_name=NAME,
            direction="hold",
            confidence=0.1,
            reasoning=f"Hypothesis error: {e}",
            weight=cfg["weight_hypothesis"],
        )


def _build_intel_context(context: Dict[str, Any]) -> str:
    """Extract intelligence context from blackboard for hypothesis prompts."""
    intel_context = ""
    blackboard = context.get("blackboard")
    if not blackboard:
        return intel_context

    intel = blackboard.metadata.get("intelligence", {})
    if intel.get("cortex_news", {}).get("data"):
        intel_context += f"\nBreaking news: {json.dumps(intel['cortex_news']['data'], default=str)[:500]}"
    if intel.get("cortex_earnings", {}).get("data"):
        intel_context += f"\nEarnings: {json.dumps(intel['cortex_earnings']['data'], default=str)[:300]}"

    social = blackboard.metadata.get("social_sentiment")
    if social:
        intel_context += f"\nSocial sentiment: {social.get('direction', 'neutral')} (score={social.get('score', 50)}, sources={social.get('sources', [])})"
        if social.get("spike"):
            intel_context += f" SPIKE: {social['spike']}"
    news_cat = blackboard.metadata.get("news_catalysts")
    if news_cat:
        intel_context += (
            f"\nNews catalysts: {news_cat.get('bullish_count', 0)} bullish, "
            f"{news_cat.get('bearish_count', 0)} bearish in {news_cat.get('headline_count', 0)} headlines"
        )
    yt = blackboard.metadata.get("youtube_knowledge")
    if yt and yt.get("entries_found", 0) > 0:
        intel_context += f"\nYouTube intel: {yt.get('ideas_count', 0)} ideas, bull/bear={yt.get('bull_signals', 0)}/{yt.get('bear_signals', 0)}"

    return intel_context


def _parse_llm_json(content: str) -> Dict[str, Any] | None:
    """Parse JSON from LLM response, handling markdown fences."""
    import re
    try:
        return json.loads(content.strip())
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# ---------------------------------------------------------------------------
# Parallel hypothesis angles (GPU Channel 6)
# ---------------------------------------------------------------------------
_HYPOTHESIS_ANGLES = [
    {
        "label": "bullish_thesis",
        "system": "You are a bullish trading analyst. Focus on upside catalysts, momentum, and reasons to buy.",
        "prompt_suffix": "Present the BULLISH case. What catalysts, momentum signals, or setups support a long entry?",
    },
    {
        "label": "bearish_thesis",
        "system": "You are a bearish trading analyst. Focus on downside risks, weakness, and reasons to sell.",
        "prompt_suffix": "Present the BEARISH case. What risks, weakness signals, or setups support a short entry or avoiding?",
    },
    {
        "label": "catalyst_analysis",
        "system": "You are a catalyst-focused analyst. Identify upcoming events, earnings, sector rotation, or macro shifts.",
        "prompt_suffix": "Identify key CATALYSTS — upcoming events, earnings, sector shifts, or macro factors that could move this stock.",
    },
    {
        "label": "risk_assessment",
        "system": "You are a risk analyst. Identify downside scenarios, stop-loss levels, and position sizing considerations.",
        "prompt_suffix": "Assess the KEY RISKS — worst-case scenarios, key levels to watch, and what could invalidate any thesis.",
    },
]


async def _hypothesis_via_router(
    symbol: str, timeframe: str, features: Dict[str, Any],
    context: Dict[str, Any], cfg: Dict[str, Any],
) -> AgentVote:
    """Generate hypothesis via 4 parallel LLM calls (GPU Channel 6).

    Fires 4 concurrent Ollama calls exploring different angles (bullish thesis,
    bearish thesis, catalyst analysis, risk assessment), then synthesizes them
    into one final hypothesis. Requires OLLAMA_NUM_PARALLEL=4 on PC2.

    Falls back to single sequential call if parallel execution fails.
    """
    from app.services.llm_router import get_llm_router, Tier

    router = get_llm_router()
    f = features.get("features", features)
    regime = str(f.get("regime", "unknown"))
    intel_context = _build_intel_context(context)

    base_info = (
        f"Symbol: {symbol}, Timeframe: {timeframe}, Regime: {regime}\n"
        f"Key features: RSI={f.get('rsi_14', '?')}, MACD={f.get('macd', '?')}, "
        f"ADX={f.get('adx_14', '?')}, Volume surge={f.get('volume_surge_ratio', '?')}\n"
        f"{intel_context}"
    )

    json_format = (
        '\nReturn JSON: {"direction": "buy"|"sell"|"hold", "confidence": 0.0-1.0, '
        '"summary": str, "risk_flags": [str]}'
    )

    # --- Fire 4 parallel angle calls ---
    async def _call_angle(angle: Dict[str, str]) -> Dict[str, Any] | None:
        """Single angle call with error isolation."""
        try:
            result = await router.route_with_fallback(
                tier=Tier.BRAINSTEM,
                messages=[
                    {"role": "system", "content": angle["system"] + " Return valid JSON only."},
                    {"role": "user", "content": f"{base_info}\n\n{angle['prompt_suffix']}{json_format}"},
                ],
                task="quick_hypothesis",
                temperature=0.3,
                max_tokens=384,
            )
            if result.error or not result.content:
                return None
            parsed = _parse_llm_json(result.content)
            if parsed:
                parsed["_angle"] = angle["label"]
                parsed["_tier"] = result.tier
            return parsed
        except Exception as e:
            logger.debug("Parallel hypothesis angle '%s' failed: %s", angle["label"], e)
            return None

    try:
        # asyncio.gather with return_exceptions=False — individual errors handled inside _call_angle
        angle_results: List[Dict[str, Any] | None] = await asyncio.gather(
            *[_call_angle(angle) for angle in _HYPOTHESIS_ANGLES]
        )
    except Exception as gather_err:
        logger.warning("Parallel hypothesis gather failed (%s), falling back to single call", gather_err)
        return await _hypothesis_single_call(symbol, timeframe, features, context, cfg)

    # Filter successful results
    valid_results = [r for r in angle_results if r is not None]
    angles_completed = len(valid_results)

    if angles_completed == 0:
        logger.warning("All 4 parallel hypothesis angles failed, falling back to single call")
        return await _hypothesis_single_call(symbol, timeframe, features, context, cfg)

    logger.info(
        "Parallel hypothesis for %s: %d/%d angles completed",
        symbol, angles_completed, len(_HYPOTHESIS_ANGLES),
    )

    # --- Synthesize results ---
    buy_votes = sum(1 for r in valid_results if r.get("direction") == "buy")
    sell_votes = sum(1 for r in valid_results if r.get("direction") == "sell")
    hold_votes = sum(1 for r in valid_results if r.get("direction") == "hold")

    confidences = [float(r.get("confidence", 0.5)) for r in valid_results]
    avg_confidence = sum(confidences) / len(confidences)

    all_risk_flags = []
    summaries = []
    for r in valid_results:
        all_risk_flags.extend(r.get("risk_flags", []))
        label = r.get("_angle", "unknown")
        summaries.append(f"[{label}] {r.get('summary', 'N/A')}")

    # Determine direction by majority vote, weighted by confidence
    buy_weight = sum(c for r, c in zip(valid_results, confidences) if r.get("direction") == "buy")
    sell_weight = sum(c for r, c in zip(valid_results, confidences) if r.get("direction") == "sell")

    if buy_weight > sell_weight and buy_votes >= sell_votes:
        direction = "buy"
    elif sell_weight > buy_weight and sell_votes >= buy_votes:
        direction = "sell"
    else:
        direction = "hold"

    # Scale confidence: strong consensus = higher, split = lower
    consensus_ratio = max(buy_votes, sell_votes, hold_votes) / angles_completed
    synth_confidence = avg_confidence * (0.7 + 0.3 * consensus_ratio)
    synth_confidence = max(0.05, min(0.99, synth_confidence))

    # Deduplicate risk flags
    unique_risk_flags = list(dict.fromkeys(all_risk_flags))

    combined_summary = " | ".join(summaries[:4])
    tier_used = valid_results[0].get("_tier", "unknown") if valid_results else "unknown"

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(synth_confidence, 2),
        reasoning=f"[Parallel/{angles_completed}angles] {combined_summary}"[:500],
        weight=cfg["weight_hypothesis"],
        metadata={
            "brain_enabled": False,
            "router_fallback": True,
            "parallel_angles": angles_completed,
            "tier": tier_used,
            "vote_split": {"buy": buy_votes, "sell": sell_votes, "hold": hold_votes},
            "avg_confidence": round(avg_confidence, 3),
            "consensus_ratio": round(consensus_ratio, 3),
            "risk_flags": unique_risk_flags[:10],
        },
    )


async def _hypothesis_single_call(
    symbol: str, timeframe: str, features: Dict[str, Any],
    context: Dict[str, Any], cfg: Dict[str, Any],
) -> AgentVote:
    """Single sequential LLM call — fallback when parallel execution fails."""
    from app.services.llm_router import get_llm_router, Tier

    router = get_llm_router()
    f = features.get("features", features)
    regime = str(f.get("regime", "unknown"))
    intel_context = _build_intel_context(context)

    prompt = (
        f"Analyze {symbol} for a {timeframe} trading hypothesis.\n"
        f"Regime: {regime}\n"
        f"Key features: RSI={f.get('rsi_14', '?')}, MACD={f.get('macd', '?')}, "
        f"ADX={f.get('adx_14', '?')}, Volume surge={f.get('volume_surge_ratio', '?')}\n"
        f"{intel_context}\n\n"
        f"Return JSON: {{\"direction\": \"buy\"|\"sell\"|\"hold\", \"confidence\": 0.0-1.0, "
        f"\"summary\": str, \"risk_flags\": [str]}}"
    )

    result = await router.route_with_fallback(
        tier=Tier.BRAINSTEM,
        messages=[
            {"role": "system", "content": "You are a trading hypothesis engine. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        task="quick_hypothesis",
        temperature=0.3,
        max_tokens=512,
    )

    if result.error or not result.content:
        raise RuntimeError(f"Router hypothesis failed: {result.error}")

    parsed = _parse_llm_json(result.content)
    if not parsed:
        raise RuntimeError("Could not parse router hypothesis response")

    direction = parsed.get("direction", "hold")
    llm_conf = float(parsed.get("confidence", 0.5))
    summary = parsed.get("summary", "Router hypothesis")

    return AgentVote(
        agent_name=NAME,
        direction=direction,
        confidence=round(llm_conf, 2),
        reasoning=f"[Router/{result.tier}] {summary}",
        weight=cfg["weight_hypothesis"],
        metadata={
            "brain_enabled": False,
            "router_fallback": True,
            "parallel_angles": 0,
            "tier": result.tier,
            "risk_flags": parsed.get("risk_flags", []),
        },
    )
