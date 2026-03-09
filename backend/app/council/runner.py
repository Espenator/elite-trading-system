"""Council Runner — orchestrates the 35-agent DAG and arbiter.

DAG execution order (parallel within stages):
  Stage 1: Perception + Academic Edge P0/P1/P2 (parallel — 13 agents)
    [market_perception, flow_perception, regime, social_perception,
     news_catalyst, youtube_knowledge, intermarket,
     gex_agent, insider_agent, finbert_sentiment_agent,
     earnings_tone_agent, dark_pool_agent, macro_regime_agent]
  Stage 2: Technical Analysis + Data Enrichment (parallel — 8 agents)
    [rsi, bbv, ema_trend, relative_strength, cycle_timing,
     supply_chain_agent, institutional_flow_agent, congressional_agent]
  Stage 3: Hypothesis + Memory (parallel — 2 agents)
    [hypothesis, layered_memory_agent]
  Stage 4: Strategy
    [strategy]
  Stage 5: Risk + Execution + Portfolio Optimization (parallel — 3 agents)
    [risk, execution, portfolio_optimizer_agent]
  Stage 5.5: Debate + Red Team (existing)
  Stage 6: Critic
  Stage 7: Arbiter (deterministic)
  Post-arbiter: [alt_data_agent] (background enrichment)

Uses BlackboardState as shared context and TaskSpawner for agent execution.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.council.blackboard import BlackboardState
from app.council.schemas import AgentVote, DecisionPacket, CognitiveMeta
from app.council.arbiter import arbitrate
from app.council.task_spawner import TaskSpawner
from app.services.cognitive_telemetry import (
    record_cognitive_snapshot, determine_cognitive_mode, get_cognitive_dashboard
)

logger = logging.getLogger(__name__)


async def run_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DecisionPacket:
    """Run the full 35-agent council and return a DecisionPacket.

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
    blackboard.council_start_ms = time.monotonic() * 1000
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

    # ── Memory Bank: recall similar past observations for this symbol ──────
    try:
        from app.knowledge.memory_bank import get_memory_bank
        memory_bank = get_memory_bank()
        f = features.get("features", features)
        regime = str(f.get("regime", "unknown")).lower()
        market_context = {
            "symbol": symbol,
            "regime": regime,
            "timeframe": timeframe,
        }
        relevant_memories = await asyncio.to_thread(
            memory_bank.recall_similar,
            agent_name="council",
            current_context=market_context,
            regime=regime,
            top_k=5,
        )
        if relevant_memories:
            if blackboard.knowledge_context is None:
                blackboard.knowledge_context = {}
            blackboard.knowledge_context["relevant_memories"] = relevant_memories
            # Compute memory-based win rate for this regime
            resolved = [m for m in relevant_memories if m.get("was_correct") is not None]
            if resolved:
                mem_win_rate = sum(1 for m in resolved if m["was_correct"]) / len(resolved)
                blackboard.knowledge_context["memory_win_rate"] = round(mem_win_rate, 3)
            logger.info(
                "Memory recall for %s: %d relevant memories (regime=%s)",
                symbol, len(relevant_memories), regime,
            )
    except Exception as e:
        logger.debug("Memory bank recall failed (proceeding): %s", e)

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
    _stage_start = time.monotonic() * 1000
    stage1_configs = [
        {"agent_type": "market_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "flow_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "regime", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "social_perception", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "news_catalyst", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "youtube_knowledge", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "intermarket", "symbol": symbol, "timeframe": timeframe, "context": context},
        # Academic Edge P0 agents
        {"agent_type": "gex_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "insider_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        # Academic Edge P1 agents
        {"agent_type": "finbert_sentiment_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "earnings_tone_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        # Academic Edge P2 agents
        {"agent_type": "dark_pool_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        # Academic Edge P4 agents (macro runs early to inform regime)
        {"agent_type": "macro_regime_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ]
    stage1 = await spawner.spawn_parallel(stage1_configs)
    all_votes.extend(stage1)
    context["stage1"] = {v.agent_name: v.to_dict() for v in stage1}
    for v in stage1:
        blackboard.perceptions[v.agent_name] = v.to_dict()
    blackboard.stage_latencies["stage1"] = time.monotonic() * 1000 - _stage_start

    # Stage 2: Technical Analysis (parallel — 5 agents)
    _stage_start = time.monotonic() * 1000
    stage2_configs = [
        {"agent_type": "rsi", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "bbv", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "ema_trend", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "relative_strength", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "cycle_timing", "symbol": symbol, "timeframe": timeframe, "context": context},
        # Academic Edge P1/P2 data enrichment agents
        {"agent_type": "supply_chain_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "institutional_flow_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "congressional_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ]
    stage2 = await spawner.spawn_parallel(stage2_configs)
    all_votes.extend(stage2)
    context["stage2"] = {v.agent_name: v.to_dict() for v in stage2}
    for v in stage2:
        blackboard.perceptions[v.agent_name] = v.to_dict()
    blackboard.stage_latencies["stage2"] = time.monotonic() * 1000 - _stage_start

    # Stage 3: Hypothesis + Memory (parallel)
    _stage_start = time.monotonic() * 1000
    stage3 = await spawner.spawn_parallel([
        {"agent_type": "hypothesis", "symbol": symbol, "timeframe": timeframe, "context": context, "model_tier": "deep"},
        {"agent_type": "layered_memory_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ])
    all_votes.extend(stage3)
    context["stage3"] = {v.agent_name: v.to_dict() for v in stage3}
    for v in stage3:
        if v.agent_name == "hypothesis":
            blackboard.hypothesis = v.to_dict()
    blackboard.stage_latencies["stage3"] = time.monotonic() * 1000 - _stage_start

    # Stage 4: Strategy
    _stage_start = time.monotonic() * 1000
    stage4 = await spawner.spawn("strategy", symbol, timeframe, context=context)
    all_votes.append(stage4)
    context["stage4"] = {stage4.agent_name: stage4.to_dict()}
    blackboard.strategy = stage4.to_dict()
    blackboard.stage_latencies["stage4"] = time.monotonic() * 1000 - _stage_start

    # Stage 5: Risk + Execution (parallel)
    _stage_start = time.monotonic() * 1000
    stage5 = await spawner.spawn_parallel([
        {"agent_type": "risk", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "execution", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "portfolio_optimizer_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ])
    all_votes.extend(stage5)
    context["stage5"] = {v.agent_name: v.to_dict() for v in stage5}
    for v in stage5:
        if v.agent_name == "risk":
            blackboard.risk_assessment = v.to_dict()
        elif v.agent_name == "execution":
            blackboard.execution_plan = v.to_dict()
    blackboard.stage_latencies["stage5"] = time.monotonic() * 1000 - _stage_start

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

    # ── ETBI: Determine cognitive mode ──────────────────────────────────
    try:
        regime_entropy = blackboard.metadata.get("regime_entropy", 0)
        homeostasis_mode = blackboard.metadata.get("homeostasis_mode", "NORMAL")
        # Get recent exploration win rate from telemetry
        from app.services.cognitive_telemetry import get_cognitive_dashboard
        dashboard = get_cognitive_dashboard()
        recent_explore_wr = dashboard.get("exploration_outcomes", {}).get("explore_win_rate")
        diversity = CognitiveMeta.compute_diversity(all_votes)

        blackboard.cognitive_mode = determine_cognitive_mode(
            regime_entropy=regime_entropy,
            homeostasis_mode=homeostasis_mode,
            recent_explore_win_rate=recent_explore_wr,
            hypothesis_diversity=diversity,
        )
        logger.info("Cognitive mode for %s: %s (entropy=%.3f, diversity=%.3f)",
                     symbol, blackboard.cognitive_mode, regime_entropy, diversity)
    except Exception as e:
        logger.debug("Cognitive mode determination failed: %s", e)

    # ── Stage 5.5: Debate + Red Team (parallel) ──────────────────────────
    # Only run if debate is enabled and we have a non-hold direction
    _stage_start = time.monotonic() * 1000
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
    blackboard.stage_latencies["stage5.5"] = time.monotonic() * 1000 - _stage_start

    # Stage 6: Critic
    _stage_start = time.monotonic() * 1000
    stage6 = await spawner.spawn("critic", symbol, timeframe, context=context)
    all_votes.append(stage6)
    context["stage6"] = {stage6.agent_name: stage6.to_dict()}
    blackboard.critic_review = stage6.to_dict()
    blackboard.stage_latencies["stage6"] = time.monotonic() * 1000 - _stage_start

    # Stage 7: Arbiter
    decision = arbitrate(symbol, timeframe, timestamp, all_votes)
    decision.council_decision_id = blackboard.council_decision_id

    # ── ETBI: Populate cognitive telemetry on DecisionPacket ────────────
    total_latency = time.monotonic() * 1000 - blackboard.council_start_ms
    cognitive = CognitiveMeta(
        mode=blackboard.cognitive_mode,
        hypothesis_diversity=CognitiveMeta.compute_diversity(all_votes),
        agent_agreement=CognitiveMeta.compute_agreement(all_votes, decision.final_direction),
        memory_precision=_compute_memory_precision(blackboard.knowledge_context),
        total_latency_ms=total_latency,
        stage_latencies=blackboard.stage_latencies,
    )
    decision.cognitive = cognitive
    decision.active_hypothesis = blackboard.hypothesis
    decision.semantic_context = blackboard.knowledge_context

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

    # Record cognitive telemetry
    try:
        record_cognitive_snapshot(
            council_decision_id=blackboard.council_decision_id,
            symbol=symbol,
            final_direction=decision.final_direction,
            final_confidence=decision.final_confidence,
            cognitive_meta=cognitive.to_dict(),
            active_hypothesis=blackboard.hypothesis,
            semantic_context=blackboard.knowledge_context,
        )
    except Exception as e:
        logger.debug("Cognitive telemetry record failed: %s", e)

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

    # NOTE: council.verdict publish is handled canonically by council_gate.py.
    # Removed duplicate publish here to prevent OrderExecutor from firing twice.
    # (council_gate.py line ~202 is the single publish point for council.verdict)

    # Post-arbiter: Alt Data Agent (background enrichment — low priority P4)
    try:
        await spawner.spawn(
            "alt_data_agent", symbol, timeframe, context=context, background=True,
        )
    except Exception:
        pass  # Alt data is purely supplementary

    return decision


def _compute_memory_precision(knowledge_context: dict) -> float:
    """Compute relevance score of recalled heuristics (0-1)."""
    if not knowledge_context:
        return 0.0
    heuristics = knowledge_context.get("active_heuristics", [])
    if not heuristics:
        return 0.0
    # Average Bayesian confidence of recalled heuristics
    confs = [h.get("bayesian_confidence", 0.5) for h in heuristics]
    return sum(confs) / len(confs) if confs else 0.0
