"""
Claude Deep Reasoning Service — the PREFRONTAL CORTEX of the CNS.

Claude handles deep reasoning tasks that require multi-step analysis,
strategy evolution, and complex trade thesis generation.

Methods:
    strategy_critic     — critique a strategy with deep reasoning
    strategy_author     — generate or evolve trading strategies
    deep_postmortem     — comprehensive post-trade analysis
    pattern_interpretation — interpret complex chart patterns
    generate_trade_thesis — build a full trade thesis
    overnight_analysis  — overnight learning and reflection
    evolve_directives   — evolve trading directive files

Usage:
    from app.services.claude_reasoning import get_claude_reasoning
    reasoning = get_claude_reasoning()
    result = await reasoning.strategy_critic(strategy_context)
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm_router import Tier, get_llm_router

logger = logging.getLogger(__name__)

_STRATEGY_SYSTEM = (
    "You are the deep reasoning engine of an elite algorithmic trading system. "
    "You think in multi-step chains, consider second-order effects, and always "
    "quantify uncertainty. Return structured JSON when requested. "
    "Be rigorous, not optimistic."
)

_POSTMORTEM_SYSTEM = (
    "You are a post-trade analysis engine. Your job is to extract maximum learning "
    "from every trade outcome. Be brutally honest about mistakes. "
    "Identify specific, actionable improvements. Return JSON."
)

_THESIS_SYSTEM = (
    "You are a trade thesis generator for an elite algorithmic trading system. "
    "Build complete trade theses with entry, exit, position sizing, and risk management. "
    "Always consider the current regime and market context. Return JSON."
)


def _parse_json_safe(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response text."""
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        pass
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError, IndexError):
                continue
    # Try finding the outermost JSON object
    brace_start = text.find('{')
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


class ClaudeReasoning:
    """Deep reasoning engine powered by Claude."""

    async def strategy_critic(self, strategy: Dict[str, Any], performance: Dict[str, Any] = None) -> Dict[str, Any]:
        """Critique a trading strategy with deep multi-step reasoning."""
        prompt = (
            "Critically analyze this trading strategy:\n\n"
            f"Strategy: {json.dumps(strategy, indent=2)}\n\n"
            f"{f'Recent Performance: {json.dumps(performance, indent=2)}' if performance else ''}\n\n"
            "Provide:\n"
            "1. Strengths and weaknesses\n"
            "2. Hidden risks or blind spots\n"
            "3. Regime sensitivity analysis\n"
            "4. Specific improvement recommendations (ordered by impact)\n"
            "5. Overall grade (A-F) with justification\n\n"
            "Return JSON: {\"grade\": str, \"strengths\": [str], \"weaknesses\": [str], "
            "\"blind_spots\": [str], \"regime_sensitivity\": {\"bull\": str, \"bear\": str, \"sideways\": str}, "
            "\"improvements\": [{\"action\": str, \"impact\": \"high\"|\"medium\"|\"low\", \"effort\": \"high\"|\"medium\"|\"low\"}], "
            "\"confidence\": 0-100}"
        )
        return await self._query(prompt, _STRATEGY_SYSTEM, "strategy_critic")

    async def strategy_author(
        self, market_context: Dict[str, Any], current_strategy: Dict[str, Any] = None,
        lessons: List[str] = None
    ) -> Dict[str, Any]:
        """Generate or evolve a trading strategy based on context and lessons."""
        prompt = (
            "Design an optimal trading strategy for the current market conditions:\n\n"
            f"Market Context: {json.dumps(market_context, indent=2)}\n\n"
            f"{f'Current Strategy: {json.dumps(current_strategy, indent=2)}' if current_strategy else 'No existing strategy — create from scratch.'}\n\n"
            f"{f'Lessons Learned: {json.dumps(lessons)}' if lessons else ''}\n\n"
            "Provide a complete strategy with:\n"
            "1. Entry criteria (specific, quantifiable)\n"
            "2. Exit criteria (take-profit and stop-loss rules)\n"
            "3. Position sizing approach\n"
            "4. Regime-specific adjustments\n"
            "5. Risk management rules\n\n"
            "Return JSON: {\"strategy_name\": str, \"regime_target\": str, "
            "\"entry_criteria\": [{\"condition\": str, \"weight\": float}], "
            "\"exit_rules\": {\"take_profit\": str, \"stop_loss\": str, \"time_stop\": str}, "
            "\"position_sizing\": str, \"regime_adjustments\": {str: str}, "
            "\"risk_rules\": [str], \"expected_win_rate\": float, \"expected_rr\": float, "
            "\"confidence\": 0-100}"
        )
        return await self._query(prompt, _STRATEGY_SYSTEM, "strategy_evolution")

    async def deep_postmortem(
        self, trade: Dict[str, Any], market_context: Dict[str, Any] = None,
        agent_votes: List[Dict] = None
    ) -> Dict[str, Any]:
        """Comprehensive post-trade analysis with learning extraction."""
        prompt = (
            "Perform a deep postmortem analysis on this trade:\n\n"
            f"Trade: {json.dumps(trade, indent=2)}\n\n"
            f"{f'Market Context at Entry: {json.dumps(market_context, indent=2)}' if market_context else ''}\n\n"
            f"{f'Agent Votes at Entry: {json.dumps(agent_votes)}' if agent_votes else ''}\n\n"
            "Analyze:\n"
            "1. Was the entry thesis correct? Why/why not?\n"
            "2. Was sizing appropriate for the risk?\n"
            "3. Was the exit optimal? Should it have been earlier/later?\n"
            "4. Which agents voted correctly? Which were wrong?\n"
            "5. What specific, actionable lessons can be extracted?\n"
            "6. Should any agent weights be adjusted? (name + direction)\n\n"
            "Return JSON: {\"entry_quality\": \"excellent\"|\"good\"|\"fair\"|\"poor\", "
            "\"sizing_quality\": str, \"exit_quality\": str, "
            "\"correct_agents\": [str], \"incorrect_agents\": [str], "
            "\"lessons\": [{\"lesson\": str, \"category\": str, \"priority\": \"high\"|\"medium\"|\"low\"}], "
            "\"weight_adjustments\": [{\"agent\": str, \"direction\": \"increase\"|\"decrease\"|\"maintain\"}], "
            "\"overall_score\": 0-100, \"key_takeaway\": str}"
        )
        return await self._query(prompt, _POSTMORTEM_SYSTEM, "deep_postmortem")

    async def pattern_interpretation(
        self, symbol: str, pattern: str, features: Dict[str, Any],
        market_context: str = ""
    ) -> Dict[str, Any]:
        """Deep interpretation of a chart pattern with multi-factor analysis."""
        prompt = (
            f"Interpret this chart pattern for {symbol}:\n\n"
            f"Pattern: {pattern}\n"
            f"Technical Features: {json.dumps(features, indent=2)}\n"
            f"{f'Market Context: {market_context}' if market_context else ''}\n\n"
            "Provide deep analysis:\n"
            "1. Pattern reliability in current regime\n"
            "2. Volume confirmation analysis\n"
            "3. Key levels to watch (support/resistance)\n"
            "4. Expected move magnitude and timeframe\n"
            "5. Invalidation criteria\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", \"pattern\": \"{pattern}\", "
            "\"reliability\": 0-100, \"volume_confirms\": bool, "
            "\"key_levels\": {\"support\": [float], \"resistance\": [float]}, "
            "\"expected_move_pct\": float, \"expected_timeframe_days\": int, "
            "\"invalidation\": str, \"trade_direction\": \"long\"|\"short\"|\"neutral\", "
            "\"confidence\": 0-100}"
        )
        return await self._query(prompt, _STRATEGY_SYSTEM, "pattern_interpretation")

    async def generate_trade_thesis(
        self, symbol: str, direction: str, context: Dict[str, Any],
        intelligence: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Build a complete trade thesis with full reasoning chain."""
        prompt = (
            f"Build a complete trade thesis for {symbol} ({direction}):\n\n"
            f"Context: {json.dumps(context, indent=2)}\n\n"
            f"{f'Intelligence Package: {json.dumps(intelligence, indent=2)}' if intelligence else ''}\n\n"
            "Create a comprehensive thesis:\n"
            "1. Core thesis (why this trade, why now)\n"
            "2. Supporting evidence (technical + fundamental)\n"
            "3. Risk factors and mitigation\n"
            "4. Entry/exit plan with specific levels\n"
            "5. Position sizing recommendation\n"
            "6. Conviction level with justification\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", \"direction\": \"{direction}\", "
            "\"thesis\": str, \"supporting_evidence\": [str], \"risk_factors\": [str], "
            "\"entry_price\": float|null, \"stop_loss\": float|null, \"target_price\": float|null, "
            "\"risk_reward_ratio\": float|null, \"position_size_pct\": float, "
            "\"conviction\": 1-10, \"timeframe\": str, \"invalidation_trigger\": str}"
        )
        return await self._query(prompt, _THESIS_SYSTEM, "trade_thesis")

    async def overnight_analysis(
        self, portfolio: Dict[str, Any], market_summary: Dict[str, Any],
        recent_trades: List[Dict] = None
    ) -> Dict[str, Any]:
        """Overnight learning and portfolio reflection."""
        prompt = (
            "Perform an overnight analysis and reflection:\n\n"
            f"Current Portfolio: {json.dumps(portfolio, indent=2)}\n\n"
            f"Market Summary: {json.dumps(market_summary, indent=2)}\n\n"
            f"{f'Recent Trades: {json.dumps(recent_trades)}' if recent_trades else ''}\n\n"
            "Analyze:\n"
            "1. Portfolio risk assessment for tomorrow\n"
            "2. Positions that need attention (stop adjustments, profit-taking)\n"
            "3. Market regime assessment for next session\n"
            "4. Key events to watch tomorrow\n"
            "5. Strategy adjustments to consider\n\n"
            "Return JSON: {\"risk_level\": \"high\"|\"medium\"|\"low\", "
            "\"positions_needing_attention\": [{\"symbol\": str, \"action\": str, \"reason\": str}], "
            "\"regime_outlook\": str, \"key_events\": [str], "
            "\"strategy_adjustments\": [str], \"overnight_risk_score\": 0-100, "
            "\"summary\": str}"
        )
        return await self._query(prompt, _STRATEGY_SYSTEM, "overnight_analysis")

    async def evolve_directives(
        self, current_directives: str, performance_data: Dict[str, Any],
        lessons: List[str] = None
    ) -> Dict[str, Any]:
        """Evolve trading directive files based on performance data."""
        prompt = (
            "Review and improve these trading directives based on recent performance:\n\n"
            f"Current Directives:\n```markdown\n{current_directives}\n```\n\n"
            f"Performance Data: {json.dumps(performance_data, indent=2)}\n\n"
            f"{f'Lessons Learned: {json.dumps(lessons)}' if lessons else ''}\n\n"
            "Provide:\n"
            "1. Specific sections that need updating\n"
            "2. New rules to add based on lessons\n"
            "3. Rules to remove or weaken (not working)\n"
            "4. The updated directive content\n\n"
            "Return JSON: {\"changes\": [{\"section\": str, \"change_type\": \"add\"|\"modify\"|\"remove\", "
            "\"description\": str}], \"updated_content\": str, \"change_count\": int, "
            "\"confidence\": 0-100}"
        )
        return await self._query(prompt, _STRATEGY_SYSTEM, "directive_evolution")

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _query(self, prompt: str, system: str, task: str) -> Dict[str, Any]:
        """Route query through LLM router's deep_cortex tier."""
        router = get_llm_router()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        result = await router.route_with_fallback(
            tier=Tier.DEEP_CORTEX,
            messages=messages,
            task=task,
            temperature=0.3,
            max_tokens=4096,
        )

        if result.error:
            logger.warning("Claude reasoning failed for %s: %s", task, result.error)
            return {"error": result.error, "task": task}

        parsed = _parse_json_safe(result.content)
        return {
            "data": parsed or {"raw_text": result.content},
            "task": task,
            "tier": result.tier,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "cost_usd": result.cost_usd,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[ClaudeReasoning] = None


def get_claude_reasoning() -> ClaudeReasoning:
    """Get or create the singleton ClaudeReasoning."""
    global _instance
    if _instance is None:
        _instance = ClaudeReasoning()
    return _instance
