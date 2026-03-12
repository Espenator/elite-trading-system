"""Council Runner — orchestrates the 33-agent DAG and arbiter.

Entry point: run_council(symbol, timeframe, features?, context?) -> DecisionPacket.
Flow: features/blackboard -> homeostasis/circuit_breaker -> Stage 1..7 -> arbitrate -> DecisionPacket.
All agents are invoked via TaskSpawner; stages run in order with parallel execution within each stage.

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


def _check_council_health(votes: List[AgentVote], total_agents: int = 33) -> dict:
    """Check council health — alert if >20% agents failed/degraded.

    An agent is considered failed if it returned direction="hold" with
    confidence=0.0 (the standard failure vote from task_spawner).
    """
    failed_agents = []
    for vote in votes:
        is_failure = (
            vote.direction == "hold"
            and vote.confidence <= 0.0
            and not vote.veto
        )
        if is_failure:
            failed_agents.append(vote.agent_name)

    failure_rate = len(failed_agents) / max(total_agents, 1)
    health = {
        "total_agents": total_agents,
        "healthy_count": len(votes) - len(failed_agents),
        "failed_count": len(failed_agents),
        "failure_rate": round(failure_rate, 3),
        "failed_agents": failed_agents,
        "is_degraded": failure_rate > 0.20,
        "is_critically_degraded": failure_rate > 0.50,
    }

    if health["is_critically_degraded"]:
        logger.critical(
            "COUNCIL CRITICALLY DEGRADED: %d/%d agents failed (%.0f%%): %s",
            len(failed_agents), total_agents, failure_rate * 100, failed_agents,
        )
    elif health["is_degraded"]:
        logger.warning(
            "COUNCIL DEGRADED: %d/%d agents failed (%.0f%%): %s",
            len(failed_agents), total_agents, failure_rate * 100, failed_agents,
        )

    return health


async def run_council(
    symbol: str,
    timeframe: str = "1d",
    features: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
) -> DecisionPacket:
    """Run the full 33-agent council and return a DecisionPacket.

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

    # Phase C (C9): Data starvation alerting (with message+severity for Slack)
    _feat_inner = features.get("features", features) if features else {}
    _data_quality = features.get("data_quality") or {}
    _quality_score = _data_quality.get("quality_score", 1.0)
    if not _feat_inner or len(_feat_inner) < 3:
        try:
            from app.core.message_bus import get_message_bus
            _starvation_bus = get_message_bus()
            asyncio.create_task(_starvation_bus.publish("alert.data_starvation", {
                "message": f"Data starvation: feature count={len(_feat_inner)} for {symbol}",
                "severity": "RED",
                "symbol": symbol,
                "feature_count": len(_feat_inner),
                "missing_hint": "Feature aggregator returned empty or near-empty dict",
            }))
        except Exception:
            pass
    elif _quality_score < 0.3:
        try:
            from app.core.message_bus import get_message_bus
            _starvation_bus = get_message_bus()
            asyncio.create_task(_starvation_bus.publish("alert.data_starvation", {
                "message": f"Data quality low for {symbol}: quality_score={_quality_score:.2f}",
                "severity": "AMBER",
                "symbol": symbol,
                "quality_score": _quality_score,
                "features_missing": _data_quality.get("features_missing", []),
            }))
        except Exception:
            pass

    # Insufficient data (no OHLCV or stale): degrade to HOLD — no trade on empty/stale features
    _is_sufficient = _data_quality.get("is_sufficient", True)
    if not _is_sufficient:
        _reason = _data_quality.get("missing_data_reason", "insufficient_data")
        logger.info(
            "Council skipping evaluation for %s: data insufficient (%s); returning HOLD",
            symbol, _reason,
        )
        _blackboard = BlackboardState(symbol=symbol, raw_features=features or {})
        return DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc).isoformat(),
            votes=[],
            final_direction="hold",
            final_confidence=0.0,
            vetoed=False,
            veto_reasons=[],
            risk_limits={},
            execution_ready=False,
            council_reasoning=f"Data insufficient for trading: {_reason}",
            council_decision_id=_blackboard.council_decision_id,
        )

    # Create BlackboardState — single source of truth for this evaluation
    blackboard = BlackboardState(
        symbol=symbol,
        raw_features=features,
    )
    blackboard.council_start_ms = time.monotonic() * 1000
    context["blackboard"] = blackboard

    # Structured logging: eval_id and trace_id for correlation
    try:
        from app.core.logging_config import eval_id, trace_id
        _token_eval = eval_id.set(blackboard.council_decision_id)
        _token_trace = trace_id.set(blackboard.council_decision_id)
    except Exception:
        _token_eval = _token_trace = None

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

    # ── Level 3A: Distributed Council — Stage 1 + Stage 2 ──────────────
    # When Brain Service (PC2) is available, offload Stage 1 perception agents
    # to PC2 while PC1 runs Stage 2 technical analysis simultaneously.
    # This cuts stage 1+2 latency from ~400-500ms sequential to ~300ms parallel.

    _stage1_agent_types = [
        "market_perception", "flow_perception", "regime", "social_perception",
        "news_catalyst", "youtube_knowledge", "intermarket",
        "gex_agent", "insider_agent",
        "finbert_sentiment_agent", "earnings_tone_agent",
        "dark_pool_agent", "macro_regime_agent",
    ]

    stage2_configs = [
        {"agent_type": "rsi", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "bbv", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "ema_trend", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "relative_strength", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "cycle_timing", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "supply_chain_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "institutional_flow_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
        {"agent_type": "congressional_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ]

    # Check if distributed council is available
    _use_distributed = False
    try:
        from app.services.brain_client import get_brain_client
        brain = get_brain_client()
        if brain.enabled and brain._circuit.can_execute():
            _use_distributed = True
    except Exception:
        pass

    _stage_start = time.monotonic() * 1000

    if _use_distributed:
        # DISTRIBUTED: PC2 runs Stage 1 perception while PC1 runs Stage 2 technical
        import json as _json
        logger.info("Distributed council: Stage 1 → PC2, Stage 2 → PC1 (parallel)")

        _feat_json = _json.dumps(features, default=str)
        _ctx_json = _json.dumps(
            {k: v for k, v in context.items() if k != "blackboard"},
            default=str,
        )

        stage1_remote_coro = brain.run_council_stage(
            symbol=symbol,
            timeframe=timeframe,
            feature_json=_feat_json,
            context_json=_ctx_json,
            stage=1,
            agent_types=_stage1_agent_types,
        )
        stage2_local_coro = spawner.spawn_parallel(stage2_configs)

        stage1_result, stage2 = await asyncio.gather(
            stage1_remote_coro, stage2_local_coro, return_exceptions=True,
        )

        # Process Stage 1 remote results
        stage1 = []
        if isinstance(stage1_result, dict) and stage1_result.get("votes"):
            for v_data in stage1_result["votes"]:
                vote = AgentVote(
                    agent_name=v_data["agent_name"],
                    direction=v_data["direction"],
                    confidence=v_data["confidence"],
                    reasoning=v_data["reasoning"],
                    veto=v_data.get("veto", False),
                    veto_reason=v_data.get("veto_reason", ""),
                    metadata=v_data.get("metadata", {}),
                    blackboard_ref=blackboard.council_decision_id,
                )
                stage1.append(vote)
            logger.info(
                "Distributed Stage 1: %d votes from PC2 in %.0fms",
                len(stage1), stage1_result.get("stage_latency_ms", 0),
            )
        else:
            # Fallback: run Stage 1 locally if PC2 failed
            logger.warning("Distributed Stage 1 failed, falling back to local")
            stage1_configs = [
                {"agent_type": at, "symbol": symbol, "timeframe": timeframe, "context": context}
                for at in _stage1_agent_types
            ]
            stage1 = await spawner.spawn_parallel(stage1_configs)

        if isinstance(stage2, Exception):
            logger.warning("Stage 2 local failed: %s", stage2)
            stage2 = []
    else:
        # LOCAL: Run Stage 1 then Stage 2 sequentially (original behavior)
        stage1_configs = [
            {"agent_type": at, "symbol": symbol, "timeframe": timeframe, "context": context}
            for at in _stage1_agent_types
        ]
        stage1 = await spawner.spawn_parallel(stage1_configs)

        blackboard.stage_latencies["stage1"] = time.monotonic() * 1000 - _stage_start
        _stage_start = time.monotonic() * 1000

        stage2 = await spawner.spawn_parallel(stage2_configs)

    # Merge Stage 1 + Stage 2 votes
    all_votes.extend(stage1)
    context["stage1"] = {v.agent_name: v.to_dict() for v in stage1}
    for v in stage1:
        blackboard.perceptions[v.agent_name] = v.to_dict()
    if "stage1" not in blackboard.stage_latencies:
        blackboard.stage_latencies["stage1"] = time.monotonic() * 1000 - _stage_start

    all_votes.extend(stage2)
    context["stage2"] = {v.agent_name: v.to_dict() for v in stage2}
    for v in stage2:
        blackboard.perceptions[v.agent_name] = v.to_dict()
    blackboard.stage_latencies["stage2"] = time.monotonic() * 1000 - _stage_start

    # Stage 3: Hypothesis + Memory (parallel — 2 agents)
    _stage_start = time.monotonic() * 1000
    stage3_configs = [
        {"agent_type": "hypothesis", "symbol": symbol, "timeframe": timeframe, "context": context, "model_tier": "deep"},
        {"agent_type": "layered_memory_agent", "symbol": symbol, "timeframe": timeframe, "context": context},
    ]
    stage3 = await spawner.spawn_parallel(stage3_configs)
    all_votes.extend(stage3)
    context["stage3"] = {v.agent_name: v.to_dict() for v in stage3}
    for v in stage3:
        if v.agent_name == "hypothesis":
            blackboard.hypothesis = v.to_dict()
            break
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

        if getattr(app_settings, "DEBATE_ENABLED", True):
            from app.council.debate.debate_engine import DebateEngine
            from app.council.agents.red_team_agent import stress_test

            # C3 fix: Run debate on ALL verdicts including HOLD to strengthen
            # HOLD conviction. For HOLD, we debate whether to BUY or SELL instead.
            debate_direction = proposed_direction
            debate_confidence = proposed_confidence
            if proposed_direction == "hold":
                # Determine which direction had the most support for the debate
                buy_weight = sum(v.confidence * v.weight for v in all_votes if v.direction == "buy")
                sell_weight = sum(v.confidence * v.weight for v in all_votes if v.direction == "sell")
                debate_direction = "buy" if buy_weight >= sell_weight else "sell"
                debate_confidence = max(buy_weight, sell_weight) / max(1, len(all_votes))
                logger.info("HOLD debate for %s: debating strongest minority direction=%s",
                            symbol, debate_direction)

            debate_engine = DebateEngine(
                max_rounds=getattr(app_settings, "DEBATE_MAX_ROUNDS", 3)
            )

            # Run debate and red team in parallel
            debate_coro = debate_engine.run_debate(
                blackboard=blackboard,
                symbol=symbol,
                proposed_direction=debate_direction,
                context=context,
            )
            red_team_coro = stress_test(
                blackboard=blackboard,
                proposed_direction=debate_direction,
                proposed_confidence=debate_confidence,
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

    # Pre-arbiter: Council health check
    health_report = _check_council_health(all_votes)
    if health_report["is_critically_degraded"]:
        logger.critical(
            "Blocking council verdict — %d/%d agents failed (%s)",
            health_report["failed_count"], health_report["total_agents"],
            health_report["failed_agents"],
        )
        decision = DecisionPacket(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            votes=all_votes,
            final_direction="hold",
            final_confidence=0.0,
            vetoed=True,
            veto_reasons=[f"{health_report['failed_count']}/{health_report['total_agents']} agents failed"],
            risk_limits={},
            execution_ready=False,
            council_reasoning="Council critically degraded — too many agents failed",
            council_decision_id=blackboard.council_decision_id,
            ttl_seconds=blackboard.ttl_seconds,
            created_at=blackboard.created_at.isoformat(),
        )
        return decision

    # Stage 7: Arbiter (pass blackboard so arbiter can inspect full context)
    decision = arbitrate(symbol, timeframe, timestamp, all_votes, blackboard=blackboard)
    decision.council_decision_id = blackboard.council_decision_id
    decision.ttl_seconds = blackboard.ttl_seconds
    decision.created_at = blackboard.created_at.isoformat()

    # ── ETBI: Populate cognitive telemetry on DecisionPacket ────────────
    total_latency = time.monotonic() * 1000 - blackboard.council_start_ms
    # Observability: record council latency and stage timings for metrics
    try:
        from app.core.metrics import gauge_set
        gauge_set("council_latency_ms", round(total_latency, 2))
        for stage_name, stage_ms in blackboard.stage_latencies.items():
            gauge_set("council_stage_duration_ms", round(stage_ms, 2), {"stage": stage_name})
    except Exception:
        pass
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
    decision.blackboard_snapshot = blackboard.to_snapshot()

    logger.info(
        "Council decision for %s [%s]: %s @ %.0f%% confidence (vetoed=%s, agents=%d)",
        symbol,
        blackboard.council_decision_id[:8],
        decision.final_direction.upper(),
        decision.final_confidence * 100,
        decision.vetoed,
        len(all_votes),
    )

    # Phase C (C4): Persist council decision audit trail to DuckDB
    try:
        import json as _json
        from app.data.duckdb_storage import duckdb_store
        _conn = duckdb_store.get_thread_cursor()
        _votes_json = _json.dumps([
            {"agent": v.agent_name, "vote": v.direction,
             "confidence": round(v.confidence, 3), "reasoning": v.reasoning[:200]}
            for v in all_votes
        ])
        _degraded = sum(1 for v in all_votes if v.direction == "hold") >= 5
        _conn.execute("""
            INSERT OR REPLACE INTO council_decisions
            (decision_id, signal_id, symbol, regime, agent_votes,
             final_verdict, final_confidence, arbiter_weighted_score,
             gate_threshold_used, was_gated, degraded, homeostasis_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            blackboard.council_decision_id,
            context.get("signal_id", ""),
            symbol,
            blackboard.regime_belief.get("state", "UNKNOWN") if blackboard.regime_belief else "UNKNOWN",
            _votes_json,
            decision.final_direction,
            round(decision.final_confidence, 4),
            round(decision.final_confidence, 4),
            context.get("gate_threshold", 65.0),
            False,
            _degraded,
            blackboard.metadata.get("homeostasis_mode", "NORMAL"),
        ])
    except Exception as _e:
        logger.debug("Council decision audit trail failed: %s", _e)

    # Phase C (C3): Record debate results to debate_history
    try:
        import json as _json
        from app.data.duckdb_storage import duckdb_store
        _debate_result = blackboard.metadata.get("debate_result")
        if _debate_result and hasattr(_debate_result, "winner"):
            _conn = duckdb_store.get_thread_cursor()
            for v in all_votes:
                if v.agent_name in ("bull_debater", "bear_debater", "red_team"):
                    _conn.execute("""
                        INSERT INTO debate_history
                        (id, debate_id, signal_id, symbol, agent_name, vote,
                         confidence, reasoning_summary, winner, quality_score, action_modifier)
                        VALUES ((SELECT COALESCE(MAX(id),0)+1 FROM debate_history),
                                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        blackboard.council_decision_id,
                        context.get("signal_id", ""),
                        symbol,
                        v.agent_name,
                        v.direction,
                        round(v.confidence, 3),
                        v.reasoning[:200] if v.reasoning else "",
                        getattr(_debate_result, "winner", ""),
                        getattr(_debate_result, "quality_score", 0.0),
                        getattr(_debate_result, "action_modifier", "neutral"),
                    ])
    except Exception as _e:
        logger.debug("Debate history recording failed: %s", _e)

    # Phase C (C9): Silent failure alerting — degraded when >20% agents are failure-HOLDs
    try:
        from app.council.council_health import update_after_evaluation, classify_votes
        total_reg = 35  # from registry
        total_latency = time.monotonic() * 1000 - blackboard.council_start_ms
        update_after_evaluation(
            decision_id=blackboard.council_decision_id,
            symbol=symbol,
            verdict=decision.final_direction,
            latency_ms=total_latency,
            votes=all_votes,
            total_registered=total_reg,
        )
        classification = classify_votes(all_votes, total_reg)
        if classification["is_degraded"]:
            from app.core.message_bus import get_message_bus
            _alert_bus = get_message_bus()
            failed_list = [v.agent_name for v in all_votes
                           if v.direction == "hold" and (v.confidence <= 0.1 or "timeout" in (v.reasoning or "").lower() or "error" in (v.reasoning or "").lower())]
            asyncio.create_task(_alert_bus.publish("alert.council_degraded", {
                "message": f"Council degraded: {classification['voted_successfully']}/{total_reg} agents healthy ({len(failed_list)} failed)",
                "severity": "RED" if classification["is_critical"] else "AMBER",
                "decision_id": blackboard.council_decision_id,
                "symbol": symbol,
                "hold_count": len(failed_list),
                "total_agents": total_reg,
                "failed_agents": failed_list,
            }))
        # Publish council.health for dashboard/observability
        try:
            from app.council.council_health import get_health
            _health_bus = get_message_bus()
            asyncio.create_task(_health_bus.publish("council.health", get_health()))
        except Exception:
            pass
    except Exception:
        pass

    # Phase C (C2): Record calibration observations for Brier scoring
    try:
        from app.council.calibration import get_calibration_tracker
        _cal = get_calibration_tracker()
        # Record each agent's confidence vs direction alignment with arbiter
        for v in all_votes:
            actual = 1.0 if v.direction == decision.final_direction else 0.0
            _cal.record(v.agent_name, v.confidence, actual)
        # Periodically persist to DuckDB (every 10 decisions)
        if hasattr(_cal, '_persist_counter'):
            _cal._persist_counter += 1
        else:
            _cal._persist_counter = 1
        if _cal._persist_counter % 10 == 0:
            _cal.persist_to_duckdb()
    except Exception as _e:
        logger.debug("Calibration recording failed: %s", _e)

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

    # Record decision in feedback loop for learning (trade_id = council_decision_id for outcome matching)
    try:
        from app.council.feedback_loop import record_decision
        record_decision(
            symbol=symbol,
            final_direction=decision.final_direction,
            votes=[v.to_dict() for v in all_votes],
            trade_id=context.get("trade_id") or blackboard.council_decision_id,
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
