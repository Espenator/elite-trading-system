"""Council Runner — orchestrates the 17-agent DAG and arbiter.

DAG execution order (parallel within stages):
  Stage 1: [market_perception, flow_perception, regime, social_perception, news_catalyst, youtube_knowledge, intermarket]
  Stage 2: [rsi, bbv, ema_trend, relative_strength, cycle_timing]
  Stage 3: [hypothesis]
  Stage 4: [strategy]
  Stage 5: [risk, execution]
  Stage 6: [critic]
  Stage 7: arbiter (deterministic)

Uses BlackboardState as shared context and TaskSpawner for agent execution.
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote, DecisionPacket
from app.council.arbiter import arbitrate
from app.council.task_spawner import TaskSpawner

logger = logging.getLogger(__name__)


async def run_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DecisionPacket:
    """Run the full 17-agent council and return a DecisionPacket.

    Args:
        symbol: Ticker symbol to evaluate
        timeframe: Timeframe (default "1d")
        features: Pre-computed feature dict. If None, auto-computes.
        context: Additional context for agents

    Returns:
        DecisionPacket with all votes and final decision
    """
    if context is None:
        context = {}

    # Auto-compute features if not provided
    if features is None:
        try:
            from app.features.feature_aggregator import aggregate
            fv = await aggregate(symbol, timeframe=timeframe)
            features = fv.to_dict()
        except Exception as e:
            logger.warning("Feature aggregation failed for %s: %s", symbol, e)
            features = {"features": {}, "symbol": symbol}

    # Create BlackboardState — single source of truth for this evaluation
    blackboard = BlackboardState(
        symbol=symbol,
        raw_features=features,
    )
    context["blackboard"] = blackboard

    timestamp = datetime.now(timezone.utc).isoformat()

    # Homeostasis — check system vitals and set mode
    try:
        from app.council.homeostasis import get_homeostasis
        homeostasis = get_homeostasis()
        vitals = await homeostasis.check_vitals()
        mode = homeostasis.get_mode()
        blackboard.metadata["homeostasis_mode"] = mode
        blackboard.metadata["position_scale"] = homeostasis.get_position_scale()
        context["homeostasis_mode"] = mode

        if mode == "HALTED":
            logger.warning("Homeostasis HALTED for %s — skipping council", symbol)
            return DecisionPacket(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                votes=[],
                final_direction="hold",
                final_confidence=0.0,
                vetoed=True,
                veto_reasons=["Homeostasis: system in HALTED mode"],
                risk_limits={},
                execution_ready=False,
                council_reasoning=f"HALTED by homeostasis: risk_score={vitals.get('risk_score', 0)}",
                council_decision_id=blackboard.council_decision_id,
            )
    except Exception as e:
        logger.debug("Homeostasis check failed (proceeding): %s", e)

    # Circuit breaker — brainstem reflexes run BEFORE the DAG
    try:
        from app.council.reflexes.circuit_breaker import circuit_breaker
        halt_reason = await circuit_breaker.check_all(blackboard)
        if halt_reason:
            logger.warning("Circuit breaker halted council for %s: %s", symbol, halt_reason)
            blackboard.metadata["circuit_breaker"] = halt_reason
            return DecisionPacket(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                votes=[],
                final_direction="hold",
                final_confidence=0.0,
                vetoed=True,
                veto_reasons=[f"Circuit breaker: {halt_reason}"],
                risk_limits={},
                execution_ready=False,
                council_reasoning=f"HALTED by circuit breaker: {halt_reason}",
                council_decision_id=blackboard.council_decision_id,
            )
    except Exception as e:
        logger.debug("Circuit breaker check failed (proceeding): %s", e)

    # Intelligence gathering — pre-council multi-tier LLM package (with timeout)
    try:
        from app.services.intelligence_orchestrator import get_intelligence_orchestrator
        from app.core.config import settings as app_settings
        if app_settings.LLM_ROUTER_ENABLED:
            orchestrator = get_intelligence_orchestrator()
            regime = str(features.get("features", {}).get("regime", "unknown"))
            intel_package = await asyncio.wait_for(
                orchestrator.prepare_intelligence_package(
                    symbol=symbol,
                    features=features,
                    regime=regime,
                    include_deep=False,  # deep cortex only for post-trade / overnight
                ),
                timeout=10.0,  # Hard 10s budget for intelligence gathering
            )
            blackboard.metadata["intelligence"] = intel_package
            logger.info(
                "Intelligence package for %s: tiers=%s, latency=%.0fms",
                symbol,
                intel_package.get("tiers_queried", []),
                intel_package.get("total_latency_ms", 0),
            )
    except asyncio.TimeoutError:
        logger.warning("Intelligence gathering timed out for %s (proceeding without)", symbol)
    except Exception as e:
        logger.debug("Intelligence gathering failed (proceeding without): %s", e)

    # ── Knowledge System: recall relevant heuristics + memories ─────────
    try:
        from app.core.config import settings as app_settings
        if getattr(app_settings, "KNOWLEDGE_SYSTEM_ENABLED", True):
            from app.knowledge.heuristic_engine import get_heuristic_engine
            from app.knowledge.knowledge_graph import get_knowledge_graph

            heuristic_engine = get_heuristic_engine()
            knowledge_graph = get_knowledge_graph()

            f = features.get("features", features)
            regime = str(f.get("regime", "unknown")).lower()

            # Get active heuristics for this regime
            active_heuristics = heuristic_engine.get_active_heuristics(regime=regime)
            active_ids = {h.heuristic_id for h in active_heuristics}

            # Get confirming cross-agent patterns
            confirmations = knowledge_graph.get_confirming_patterns(active_ids)
            contradictions = knowledge_graph.get_contradictions(active_ids)

            blackboard.knowledge_context = {
                "active_heuristics": [h.to_dict() for h in active_heuristics[:10]],
                "confirmations": confirmations[:5],
                "contradictions": contradictions[:5],
                "total_heuristics": len(active_heuristics),
            }

            if active_heuristics:
                logger.info(
                    "Knowledge context for %s: %d heuristics, %d confirmations, %d contradictions",
                    symbol, len(active_heuristics), len(confirmations), len(contradictions),
                )
    except Exception as e:
        logger.debug("Knowledge system recall failed (proceeding): %s", e)

    # Initialize TaskSpawner with all agents
    spawner = TaskSpawner(blackboard)
    spawner.register_all_agents()

    # Check self-awareness for hibernated agents
    try:
        from app.council.self_awareness import get_self_awareness
        sa = get_self_awareness()
        for agent_name in list(spawner.registered_agents):
            if sa.should_skip_agent(agent_name):
                logger.warning("Skipping hibernated/unhealthy agent: %s", agent_name)
                spawner._registry.pop(agent_name, None)
    except Exception:
        pass  # Self-awareness unavailable, proceed with all agents

    all_votes: List[AgentVote] = []

    # Stage 1: Perception + Data Sources + Intermarket (parallel — 7 agents)
    stage1 = await spawner.spawn_parallel([
        {"agent_type": "market_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "flow_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "regime", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "social_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "news_catalyst", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "youtube_knowledge", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "intermarket", "symbol": symbol, "timeframe": timeframe, "context": context},
    ])
    all_votes.extend(stage1)
    context["stage1"] = {v.agent_name: v.to_dict() for v in stage1}
    for v in stage1:
        blackboard.perceptions[v.agent_name] = v.to_dict()

    # Stage 2: Technical Analysis (parallel — 5 agents)
    stage2 = await spawner.spawn_parallel([
        {"agent_type": "rsi", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "bbv", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "ema_trend", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "relative_strength", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "cycle_timing", "symbol": symbol, "timeframe": timeframe, "context": context},
    ])
    all_votes.extend(stage2)
    context["stage2"] = {v.agent_name: v.to_dict() for v in stage2}
    for v in stage2:
        blackboard.perceptions[v.agent_name] = v.to_dict()

    # Stage 3: Hypothesis (deep model tier for LLM)
    stage3 = await spawner.spawn("hypothesis", symbol, timeframe, context=context, model_tier="deep")
    all_votes.append(stage3)
    context["stage3"] = {stage3.agent_name: stage3.to_dict()}
    blackboard.hypothesis = stage3.to_dict()

    # Stage 4: Strategy
    stage4 = await spawner.spawn("strategy", symbol, timeframe, context=context)
    all_votes.append(stage4)
    context["stage4"] = {stage4.agent_name: stage4.to_dict()}
    blackboard.strategy = stage4.to_dict()

    # Stage 5: Risk + Execution (parallel)
    stage5 = await spawner.spawn_parallel([
        {"agent_type": "risk", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "execution", "symbol": symbol, "timeframe": timeframe, "context": context},
    ])
    all_votes.extend(stage5)
    context["stage5"] = {v.agent_name: v.to_dict() for v in stage5}
    for v in stage5:
        if v.agent_name == "risk":
            blackboard.risk_assessment = v.to_dict()
        elif v.agent_name == "execution":
            blackboard.execution_plan = v.to_dict()

    # ── Bayesian Regime Update ────────────────────────────────────────────
    try:
        from app.council.regime.bayesian_regime import (
            get_bayesian_regime, compute_likelihoods,
        )
        bayes_regime = get_bayesian_regime()
        f = features.get("features", features)
        likelihoods = compute_likelihoods(
            vix=float(f.get("vix_close", 20)),
            trend_strength=float(f.get("adx_14", 25)) / 50.0 - 0.5,  # normalize to [-0.5, 0.5]
            breadth_ratio=float(f.get("breadth_ratio", 0.5)),
            volatility_ratio=float(f.get("atr_14", 1)) / float(f.get("atr_21", 1)) if f.get("atr_21") else 1.0,
        )
        bayes_regime.update(likelihoods)
        blackboard.regime_belief = bayes_regime.get_beliefs()
        blackboard.metadata["regime_entropy"] = bayes_regime.entropy()
        blackboard.metadata["regime_position_modifier"] = bayes_regime.position_size_modifier()
        dom_regime, dom_prob = bayes_regime.dominant_regime()
        logger.info(
            "Bayesian regime for %s: %s (%.0f%%), entropy=%.3f, position_mod=%.2f",
            symbol, dom_regime, dom_prob * 100,
            bayes_regime.entropy(), bayes_regime.position_size_modifier(),
        )
    except Exception as e:
        logger.debug("Bayesian regime update failed (proceeding): %s", e)

    # ── Stage 5.5: Debate + Red Team (parallel) ──────────────────────────
    # Only run if debate is enabled and we have a non-hold direction
    try:
        from app.core.config import settings as app_settings
        proposed_direction = "hold"
        proposed_confidence = 0.0
        for v in all_votes:
            if v.agent_name == "strategy" and v.direction != "hold":
                proposed_direction = v.direction
                proposed_confidence = v.confidence
                break

        if getattr(app_settings, "DEBATE_ENABLED", True) and proposed_direction != "hold":
            from app.council.debate.debate_engine import DebateEngine
            from app.council.agents.red_team_agent import stress_test

            debate_engine = DebateEngine(
                max_rounds=getattr(app_settings, "DEBATE_MAX_ROUNDS", 3)
            )

            # Run debate and red team in parallel
            debate_coro = debate_engine.run_debate(
                blackboard=blackboard,
                symbol=symbol,
                proposed_direction=proposed_direction,
                context=context,
            )
            red_team_coro = stress_test(
                blackboard=blackboard,
                proposed_direction=proposed_direction,
                proposed_confidence=proposed_confidence,
                context=context,
            )

            debate_result, red_team_report = await asyncio.gather(
                debate_coro, red_team_coro, return_exceptions=True,
            )

            # Process debate result
            if isinstance(debate_result, Exception):
                logger.warning("Debate engine error: %s", debate_result)
            else:
                blackboard.debate = debate_result.to_dict()
                context["debate"] = debate_result.to_dict()
                logger.info(
                    "Debate for %s: winner=%s, quality=%.2f, modifier=%s",
                    symbol, debate_result.winner, debate_result.quality_score,
                    debate_result.action_modifier,
                )
                # If debate says veto, create a veto vote
                if debate_result.action_modifier == "veto":
                    veto_vote = AgentVote(
                        agent_name="debate_engine",
                        direction="hold",
                        confidence=0.9,
                        reasoning=f"Debate VETO: {debate_result.judge_summary[:200]}",
                        veto=True,
                        veto_reason="Debate engine veto: bear case overwhelmingly stronger",
                        metadata={"debate_score": debate_result.quality_score},
                        blackboard_ref=blackboard.council_decision_id,
                    )
                    all_votes.append(veto_vote)

            # Process red team result
            if isinstance(red_team_report, Exception):
                logger.warning("Red team error: %s", red_team_report)
            else:
                blackboard.red_team_report = red_team_report.to_dict()
                context["red_team"] = red_team_report.to_dict()
                # Create red team vote
                red_team_vote = AgentVote(
                    agent_name="red_team",
                    direction="hold" if red_team_report.overall_recommendation == "REJECT" else proposed_direction,
                    confidence=0.7 if red_team_report.overall_recommendation == "PROCEED" else 0.4,
                    reasoning=f"Red team: {red_team_report.overall_recommendation} "
                              f"(survived={red_team_report.scenarios_survived}/{red_team_report.total_scenarios})",
                    veto=(red_team_report.overall_recommendation == "REJECT"),
                    veto_reason=f"Stress test REJECT: worst_case={red_team_report.worst_case_loss_pct:.1%}"
                                if red_team_report.overall_recommendation == "REJECT" else "",
                    metadata=red_team_report.to_dict(),
                    blackboard_ref=blackboard.council_decision_id,
                )
                all_votes.append(red_team_vote)

    except Exception as e:
        logger.debug("Stage 5.5 (debate/red-team) failed (proceeding): %s", e)

    # Stage 6: Critic
    stage6 = await spawner.spawn("critic", symbol, timeframe, context=context)
    all_votes.append(stage6)
    context["stage6"] = {stage6.agent_name: stage6.to_dict()}
    blackboard.critic_review = stage6.to_dict()

    # Stage 7: Arbiter
    decision = arbitrate(symbol, timeframe, timestamp, all_votes)
    decision.council_decision_id = blackboard.council_decision_id

    logger.info(
        "Council decision for %s [%s]: %s @ %.0f%% confidence (vetoed=%s, agents=%d)",
        symbol,
        blackboard.council_decision_id[:8],
        decision.final_direction.upper(),
        decision.final_confidence * 100,
        decision.vetoed,
        len(all_votes),
    )

    # HITL gate — check if human approval is required before execution
    try:
        from app.council.hitl_gate import get_hitl_gate
        hitl = get_hitl_gate()
        hitl_result = hitl.check(
            decision={
                "council_decision_id": blackboard.council_decision_id,
                "symbol": symbol,
                "final_direction": decision.final_direction,
                "final_confidence": decision.final_confidence,
                "vetoed": decision.vetoed,
                "metadata": blackboard.metadata,
            },
            portfolio_context=context.get("portfolio_context"),
        )
        if hitl_result.requires_approval:
            decision.execution_ready = False
            decision.council_reasoning += (
                f" | HITL: awaiting approval ({', '.join(hitl_result.gates_triggered)})"
            )
            blackboard.metadata["hitl_pending"] = hitl_result.to_dict()
            await hitl.request_approval(hitl_result)
    except Exception as e:
        logger.debug("HITL gate check failed (proceeding): %s", e)

    # Record decision in feedback loop for learning
    try:
        from app.council.feedback_loop import record_decision
        record_decision(
            symbol=symbol,
            final_direction=decision.final_direction,
            votes=[v.to_dict() for v in all_votes],
            trade_id=context.get("trade_id"),
        )
    except Exception as e:
        logger.debug("Feedback loop record failed: %s", e)

    # ── Knowledge System: store agent memories for compound learning ──
    # Batch embedding generation to avoid 17 serial GPU calls on the hot path
    try:
        from app.core.config import settings as app_settings
        if getattr(app_settings, "KNOWLEDGE_SYSTEM_ENABLED", True):
            from app.knowledge.memory_bank import get_memory_bank, AgentMemory
            from app.knowledge.embedding_service import get_embedding_engine

            bank = get_memory_bank()
            embed_engine = get_embedding_engine()
            f = features.get("features", features)
            regime = str(f.get("regime", "unknown")).lower()
            trade_id = context.get("trade_id", blackboard.council_decision_id)

            market_ctx = {
                k: v for k, v in f.items()
                if isinstance(v, (int, float, str)) and k in (
                    "rsi_14", "macd", "atr_14", "adx_14", "sma_20",
                    "sma_50", "volume", "close", "vix_close",
                )
            }

            # Build all memories and embedding texts upfront
            memories = []
            embed_texts = []
            for vote in all_votes:
                obs = {
                    "direction": vote.direction,
                    "confidence": vote.confidence,
                    "reasoning": vote.reasoning[:200],
                }
                memory = AgentMemory(
                    agent_name=vote.agent_name,
                    symbol=symbol,
                    regime=regime,
                    market_context=market_ctx,
                    agent_observation=obs,
                    agent_vote=vote.direction,
                    confidence=vote.confidence,
                    trade_id=trade_id,
                )
                memories.append(memory)
                embed_texts.append(bank._context_to_text(market_ctx | obs, regime))

            # Single batched embedding call instead of N serial calls
            embeddings = embed_engine.embed(embed_texts)
            for memory, embedding in zip(memories, embeddings):
                memory.embedding = embedding
                bank.store_observation(memory)
    except Exception as e:
        logger.debug("Knowledge memory storage failed: %s", e)

    # Publish enhanced verdict to message bus + WebSocket
    try:
        from app.core.message_bus import get_message_bus
        bus = get_message_bus()
        if bus._running:
            verdict_payload = {
                "type": "council_verdict",
                "council_decision_id": blackboard.council_decision_id,
                "symbol": symbol,
                "direction": decision.final_direction,
                "confidence": decision.final_confidence,
                "agent_votes": [v.to_dict() for v in all_votes],
                "circuit_breaker": blackboard.metadata.get("circuit_breaker"),
                "timestamp": timestamp,
                "vetoed": decision.vetoed,
                "execution_ready": decision.execution_ready,
                "council_reasoning": decision.council_reasoning,
            }
            await bus.publish("council.verdict", verdict_payload)
    except Exception:
        pass

    return decision
