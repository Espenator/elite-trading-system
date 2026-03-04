"""Hypothesis Agent — LLM-powered hypothesis via Brain Service."""
import json
import logging
from typing import Any, Dict

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


async def _hypothesis_via_router(
    symbol: str, timeframe: str, features: Dict[str, Any],
    context: Dict[str, Any], cfg: Dict[str, Any],
) -> AgentVote:
    """Fallback: generate hypothesis via LLM router when brain service is disabled."""
    from app.services.llm_router import get_llm_router, Tier

    router = get_llm_router()
    f = features.get("features", features)
    regime = str(f.get("regime", "unknown"))

    # Build context from blackboard intelligence if available
    intel_context = ""
    blackboard = context.get("blackboard")
    if blackboard:
        intel = blackboard.metadata.get("intelligence", {})
        if intel.get("cortex_news", {}).get("data"):
            intel_context += f"\nBreaking news: {json.dumps(intel['cortex_news']['data'], default=str)[:500]}"
        if intel.get("cortex_earnings", {}).get("data"):
            intel_context += f"\nEarnings: {json.dumps(intel['cortex_earnings']['data'], default=str)[:300]}"

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

    # Parse JSON response
    import re
    parsed = None
    try:
        parsed = json.loads(result.content.strip())
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', result.content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                pass

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
            "tier": result.tier,
            "risk_flags": parsed.get("risk_flags", []),
        },
    )
