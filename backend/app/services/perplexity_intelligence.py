"""
Perplexity Real-Time Intelligence — web-grounded market intelligence via Sonar Pro.

Perplexity is the EYES of the CNS: it sees what's happening in the world right now.
Every method returns structured intelligence that flows into the BlackboardState
before council agents vote.

Methods:
    scan_breaking_news      — breaking news affecting a symbol
    analyze_earnings        — earnings context and estimates
    scan_sector_rotation    — sector/industry rotation signals
    get_fear_greed_context  — market fear/greed web context
    scan_fed_macro          — Fed, macro, and economic data
    get_institutional_flow  — institutional activity signals
    search_pattern_context  — validate chart patterns against real-world catalysts

Usage:
    from app.services.perplexity_intelligence import get_perplexity_intel
    intel = get_perplexity_intel()
    news = await intel.scan_breaking_news("AAPL")
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm_router import Tier, get_llm_router

logger = logging.getLogger(__name__)

# System prompts for each intelligence type
_NEWS_SYSTEM = (
    "You are a financial news analyst for an algorithmic trading system. "
    "Return ONLY valid JSON. Be concise, factual, and time-sensitive. "
    "Focus on price-moving catalysts, not background information."
)

_EARNINGS_SYSTEM = (
    "You are an earnings analyst for an algorithmic trading system. "
    "Return ONLY valid JSON with earnings dates, estimates, and key metrics."
)

_SECTOR_SYSTEM = (
    "You are a sector rotation analyst. Return ONLY valid JSON. "
    "Identify which sectors money is flowing into/out of right now."
)

_MACRO_SYSTEM = (
    "You are a macro-economic analyst for an algorithmic trading system. "
    "Return ONLY valid JSON. Focus on Fed policy, yields, and economic data."
)

_FLOW_SYSTEM = (
    "You are an institutional flow analyst. Return ONLY valid JSON. "
    "Identify dark pool activity, block trades, and smart money signals."
)


def _parse_json_safe(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response text."""
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, TypeError):
        pass
    # Try markdown code blocks
    patterns = [
        r'```json\s*\n(.*?)\n\s*```',
        r'```\s*\n(.*?)\n\s*```',
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group())
            except (json.JSONDecodeError, TypeError, IndexError):
                continue
    return None


class PerplexityIntelligence:
    """Real-time market intelligence powered by Perplexity Sonar Pro."""

    async def scan_breaking_news(self, symbol: str, context: str = "") -> Dict[str, Any]:
        """Scan for breaking news affecting a symbol."""
        prompt = (
            f"What is the most recent breaking news for {symbol} stock in the last 24 hours? "
            f"Focus on: earnings surprises, FDA decisions, M&A, management changes, "
            f"analyst upgrades/downgrades, guidance changes, legal/regulatory actions. "
            f"{f'Additional context: {context}' if context else ''}\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", \"headlines\": ["
            f"{{\"title\": str, \"impact\": \"bullish\"|\"bearish\"|\"neutral\", "
            f"\"magnitude\": 1-10, \"time_ago\": str}}], "
            f"\"overall_sentiment\": \"bullish\"|\"bearish\"|\"neutral\", "
            f"\"catalyst_score\": 0-100}}"
        )
        return await self._query(prompt, _NEWS_SYSTEM, "breaking_news", symbol)

    async def analyze_earnings(self, symbol: str) -> Dict[str, Any]:
        """Get earnings context: dates, estimates, whisper numbers, history."""
        prompt = (
            f"For {symbol} stock, provide current earnings information:\n"
            f"1. Next earnings date and time (pre/post market)\n"
            f"2. Consensus EPS estimate vs whisper number\n"
            f"3. Revenue estimate\n"
            f"4. Last 4 quarters: beat/miss and stock reaction\n"
            f"5. Key metrics analysts are watching\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", \"next_earnings_date\": str, "
            f"\"days_until_earnings\": int, \"eps_estimate\": float, "
            f"\"revenue_estimate_b\": float, \"whisper_eps\": float|null, "
            f"\"last_4q\": [{{\"quarter\": str, \"beat\": bool, \"surprise_pct\": float, "
            f"\"stock_reaction_pct\": float}}], \"key_metrics\": [str], "
            f"\"earnings_risk\": \"high\"|\"medium\"|\"low\"}}"
        )
        return await self._query(prompt, _EARNINGS_SYSTEM, "earnings_context", symbol)

    async def scan_sector_rotation(self, sectors: List[str] = None) -> Dict[str, Any]:
        """Scan for sector rotation signals across the market."""
        sector_list = ", ".join(sectors) if sectors else "Technology, Healthcare, Financials, Energy, Consumer, Industrials"
        prompt = (
            f"Analyze current sector rotation in the US stock market across: {sector_list}.\n"
            f"1. Which sectors are seeing inflows vs outflows this week?\n"
            f"2. Any notable sector ETF volume spikes?\n"
            f"3. Rotation signals from institutional positioning?\n\n"
            f"Return JSON: {{\"sectors\": [{{\"name\": str, \"flow\": \"inflow\"|\"outflow\"|\"neutral\", "
            f"\"strength\": 1-10, \"key_driver\": str}}], "
            f"\"rotation_theme\": str, \"risk_on\": bool}}"
        )
        return await self._query(prompt, _SECTOR_SYSTEM, "sector_rotation")

    async def get_fear_greed_context(self) -> Dict[str, Any]:
        """Get current market fear/greed context from web sources."""
        prompt = (
            "What is the current state of market fear and greed? Include:\n"
            "1. CNN Fear & Greed Index value and trend\n"
            "2. VIX level and recent trajectory\n"
            "3. Put/Call ratio context\n"
            "4. Market breadth indicators\n"
            "5. Overall market sentiment from social media and news\n\n"
            "Return JSON: {\"fear_greed_value\": int, \"fear_greed_label\": str, "
            "\"vix_level\": float, \"vix_trend\": \"rising\"|\"falling\"|\"stable\", "
            "\"put_call_ratio\": float, \"breadth\": \"positive\"|\"negative\"|\"neutral\", "
            "\"social_sentiment\": \"bullish\"|\"bearish\"|\"neutral\", "
            "\"contrarian_signal\": str|null}"
        )
        return await self._query(prompt, _MACRO_SYSTEM, "fear_greed_context")

    async def scan_fed_macro(self) -> Dict[str, Any]:
        """Scan for Fed policy and macro-economic developments."""
        prompt = (
            "What are the latest Fed and macro-economic developments?\n"
            "1. Latest Fed commentary or meeting notes\n"
            "2. Rate expectations (CME FedWatch)\n"
            "3. Key economic data releases this week\n"
            "4. Treasury yield movements\n"
            "5. Dollar index trend\n\n"
            "Return JSON: {\"fed_stance\": \"hawkish\"|\"dovish\"|\"neutral\", "
            "\"rate_cut_probability\": float, \"next_fomc_date\": str, "
            "\"key_data_releases\": [{\"name\": str, \"date\": str, \"impact\": str}], "
            "\"yield_10y\": float, \"dxy_trend\": \"rising\"|\"falling\"|\"stable\", "
            "\"macro_risk\": \"high\"|\"medium\"|\"low\"}"
        )
        return await self._query(prompt, _MACRO_SYSTEM, "macro_context")

    async def get_institutional_flow(self, symbol: str) -> Dict[str, Any]:
        """Get institutional activity signals for a symbol."""
        prompt = (
            f"What is the recent institutional activity for {symbol}?\n"
            f"1. Recent 13F filings or institutional buys/sells\n"
            f"2. Dark pool activity signals\n"
            f"3. Block trade activity\n"
            f"4. Short interest changes\n"
            f"5. Insider transactions\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", "
            f"\"institutional_sentiment\": \"accumulating\"|\"distributing\"|\"neutral\", "
            f"\"dark_pool_signal\": str|null, \"short_interest_pct\": float|null, "
            f"\"insider_activity\": str|null, \"notable_holders\": [str], "
            f"\"confidence\": 0-100}}"
        )
        return await self._query(prompt, _FLOW_SYSTEM, "institutional_flow", symbol)

    async def search_pattern_context(self, symbol: str, pattern: str, timeframe: str = "1d") -> Dict[str, Any]:
        """Validate a chart pattern against real-world catalysts."""
        prompt = (
            f"{symbol} is showing a {pattern} pattern on the {timeframe} chart. "
            f"Is there a fundamental catalyst that supports or contradicts this pattern?\n"
            f"1. Any recent news that explains the price action?\n"
            f"2. Upcoming catalysts that could confirm/invalidate?\n"
            f"3. Similar patterns in this stock historically — outcome?\n\n"
            f"Return JSON: {{\"symbol\": \"{symbol}\", \"pattern\": \"{pattern}\", "
            f"\"catalyst_found\": bool, \"catalyst_description\": str, "
            f"\"supports_pattern\": bool, \"upcoming_risks\": [str], "
            f"\"historical_hit_rate\": float|null, \"confidence\": 0-100}}"
        )
        return await self._query(prompt, _NEWS_SYSTEM, "pattern_context", symbol)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _query(
        self, prompt: str, system: str, task: str, symbol: str = None
    ) -> Dict[str, Any]:
        """Route query through LLM router's cortex tier."""
        router = get_llm_router()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        result = await router.route_with_fallback(
            tier=Tier.CORTEX,
            messages=messages,
            task=task,
            temperature=0.2,
            max_tokens=2048,
        )

        if result.error:
            logger.warning("Perplexity query failed for %s/%s: %s", task, symbol or "market", result.error)
            return {"error": result.error, "task": task, "symbol": symbol}

        parsed = _parse_json_safe(result.content)
        return {
            "data": parsed or {"raw_text": result.content},
            "task": task,
            "symbol": symbol,
            "tier": result.tier,
            "model": result.model,
            "latency_ms": result.latency_ms,
            "citations": result.citations,
            "cost_usd": result.cost_usd,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[PerplexityIntelligence] = None


def get_perplexity_intel() -> PerplexityIntelligence:
    """Get or create the singleton PerplexityIntelligence."""
    global _instance
    if _instance is None:
        _instance = PerplexityIntelligence()
    return _instance
