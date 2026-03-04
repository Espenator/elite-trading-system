"""
Intelligence Orchestrator — coordinates all three LLM tiers into a unified
intelligence package before the council runs.

This is the "pre-frontal cortex" coordination layer:
    1. Gathers real-time intelligence from Perplexity (cortex/eyes)
    2. Optionally enriches with Claude deep reasoning
    3. Packages results into blackboard.metadata["intelligence"]
    4. Council agents then consume this pre-gathered intelligence

Methods:
    prepare_intelligence_package — parallel gather before council
    validate_pattern_with_context — cross-validate pattern + news
    run_overnight_learning — overnight batch analysis

Usage:
    from app.services.intelligence_orchestrator import get_intelligence_orchestrator
    orchestrator = get_intelligence_orchestrator()
    intel = await orchestrator.prepare_intelligence_package("AAPL", features, regime)
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.llm_router import Tier, get_llm_router
from app.services.perplexity_intelligence import get_perplexity_intel
from app.services.claude_reasoning import get_claude_reasoning
from app.core.config import settings

logger = logging.getLogger(__name__)


class IntelligenceOrchestrator:
    """Coordinates multi-tier intelligence gathering for the council."""

    async def prepare_intelligence_package(
        self,
        symbol: str,
        features: Dict[str, Any] = None,
        regime: str = "unknown",
        include_deep: bool = False,
    ) -> Dict[str, Any]:
        """Gather intelligence from all available tiers in parallel.

        This runs BEFORE the council DAG, writing results to the intelligence
        package that agents can read from blackboard.metadata["intelligence"].

        Args:
            symbol: Ticker symbol
            features: Pre-computed feature dict
            regime: Current market regime
            include_deep: Whether to include Claude deep analysis (slower)

        Returns:
            Intelligence package dict with results from all tiers
        """
        t0 = time.time()
        intel = get_perplexity_intel()
        package: Dict[str, Any] = {
            "symbol": symbol,
            "regime": regime,
            "gathered_at": time.time(),
            "tiers_queried": [],
            "errors": [],
        }

        # ── Parallel cortex queries (Perplexity) ─────────────────────────────
        cortex_tasks = {}
        if settings.PERPLEXITY_API_KEY:
            cortex_tasks["news"] = intel.scan_breaking_news(symbol)
            cortex_tasks["earnings"] = intel.analyze_earnings(symbol)
            cortex_tasks["institutional"] = intel.get_institutional_flow(symbol)
            cortex_tasks["fear_greed"] = intel.get_fear_greed_context()
            package["tiers_queried"].append("cortex")

        # ── Brainstem quick summary (Ollama) ─────────────────────────────────
        router = get_llm_router()
        brainstem_task = None
        if features:
            feature_summary = self._build_feature_summary(features, regime)
            brainstem_task = router.route(
                tier=Tier.BRAINSTEM,
                messages=[
                    {"role": "system", "content": "You are a fast market signal analyst. Return JSON."},
                    {"role": "user", "content": feature_summary},
                ],
                task="feature_summary",
                temperature=0.2,
                max_tokens=512,
                timeout=5.0,
            )
            package["tiers_queried"].append("brainstem")

        # ── Gather all parallel results ──────────────────────────────────────
        all_tasks = {}
        for key, coro in cortex_tasks.items():
            all_tasks[f"cortex_{key}"] = coro
        if brainstem_task:
            all_tasks["brainstem_summary"] = brainstem_task

        if all_tasks:
            results = await asyncio.gather(
                *all_tasks.values(), return_exceptions=True,
            )
            for key, result in zip(all_tasks.keys(), results):
                if isinstance(result, Exception):
                    logger.warning("Intelligence gather %s failed: %s", key, result)
                    package["errors"].append({"source": key, "error": str(result)})
                else:
                    if isinstance(result, dict):
                        package[key] = result
                    else:
                        # LLMResponse from brainstem
                        package[key] = {"content": result.content, "tier": result.tier, "latency_ms": result.latency_ms}

        # ── Optional deep cortex enrichment (Claude) ─────────────────────────
        if include_deep and settings.ANTHROPIC_API_KEY:
            try:
                reasoning = get_claude_reasoning()
                context = {
                    "symbol": symbol,
                    "regime": regime,
                    "news": package.get("cortex_news", {}).get("data", {}),
                    "features_summary": package.get("brainstem_summary", {}).get("content", ""),
                }
                thesis = await reasoning.generate_trade_thesis(
                    symbol=symbol,
                    direction="evaluate",
                    context=context,
                )
                package["deep_cortex_thesis"] = thesis
                package["tiers_queried"].append("deep_cortex")
            except Exception as e:
                logger.warning("Deep cortex enrichment failed: %s", e)
                package["errors"].append({"source": "deep_cortex_thesis", "error": str(e)})

        package["total_latency_ms"] = (time.time() - t0) * 1000
        logger.info(
            "Intelligence package for %s gathered in %.0fms (tiers: %s, errors: %d)",
            symbol, package["total_latency_ms"],
            ", ".join(package["tiers_queried"]),
            len(package["errors"]),
        )
        return package

    async def validate_pattern_with_context(
        self, symbol: str, pattern: str, features: Dict[str, Any],
        timeframe: str = "1d",
    ) -> Dict[str, Any]:
        """Cross-validate a chart pattern against real-world news/catalysts.

        Runs Perplexity pattern context search + Claude pattern interpretation
        in parallel, then combines results.
        """
        intel = get_perplexity_intel()
        reasoning = get_claude_reasoning()

        tasks = {
            "news_context": intel.search_pattern_context(symbol, pattern, timeframe),
            "deep_interpretation": reasoning.pattern_interpretation(
                symbol, pattern, features,
                market_context=f"Pattern: {pattern} on {timeframe}",
            ),
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        validation = {"symbol": symbol, "pattern": pattern}

        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                validation[key] = {"error": str(result)}
            else:
                validation[key] = result

        # Combine confidence scores
        news_conf = 0
        deep_conf = 0
        if isinstance(validation.get("news_context"), dict):
            data = validation["news_context"].get("data", {})
            news_conf = data.get("confidence", 0)
        if isinstance(validation.get("deep_interpretation"), dict):
            data = validation["deep_interpretation"].get("data", {})
            deep_conf = data.get("confidence", 0)

        validation["combined_confidence"] = (news_conf * 0.4 + deep_conf * 0.6)
        return validation

    async def run_overnight_learning(
        self, portfolio: Dict[str, Any], market_summary: Dict[str, Any],
        recent_trades: List[Dict] = None, directives_content: str = None,
    ) -> Dict[str, Any]:
        """Overnight batch analysis: portfolio review + directive evolution.

        Runs Claude deep analysis on portfolio, trades, and optionally evolves directives.
        """
        reasoning = get_claude_reasoning()
        results: Dict[str, Any] = {"timestamp": time.time()}

        # Overnight portfolio analysis
        try:
            analysis = await reasoning.overnight_analysis(
                portfolio=portfolio,
                market_summary=market_summary,
                recent_trades=recent_trades,
            )
            results["overnight_analysis"] = analysis
        except Exception as e:
            logger.warning("Overnight analysis failed: %s", e)
            results["overnight_analysis"] = {"error": str(e)}

        # Directive evolution (if content provided)
        if directives_content and recent_trades:
            try:
                lessons = []
                for t in (recent_trades or []):
                    if t.get("lesson"):
                        lessons.append(t["lesson"])

                performance = {
                    "total_trades": len(recent_trades or []),
                    "win_rate": sum(1 for t in recent_trades if t.get("pnl", 0) > 0) / max(len(recent_trades), 1),
                    "avg_pnl": sum(t.get("pnl", 0) for t in recent_trades) / max(len(recent_trades), 1),
                }
                evolution = await reasoning.evolve_directives(
                    current_directives=directives_content,
                    performance_data=performance,
                    lessons=lessons or None,
                )
                results["directive_evolution"] = evolution
            except Exception as e:
                logger.warning("Directive evolution failed: %s", e)
                results["directive_evolution"] = {"error": str(e)}

        return results

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_feature_summary(self, features: Dict[str, Any], regime: str) -> str:
        """Build a concise feature summary prompt for brainstem analysis."""
        f = features.get("features", features)
        lines = [f"Symbol: {features.get('symbol', '?')}", f"Regime: {regime}"]

        # Extract key technical indicators
        for key in ["rsi_14", "macd", "macd_signal", "sma_20", "sma_50", "sma_200",
                     "atr_14", "adx_14", "bb_upper", "bb_lower", "volume"]:
            if key in f:
                lines.append(f"  {key}: {f[key]}")

        lines.append("\nProvide a quick JSON signal assessment: {\"signal\": \"bullish\"|\"bearish\"|\"neutral\", "
                      "\"strength\": 1-10, \"key_factor\": str}")
        return "\n".join(lines)


# ── Singleton ─────────────────────────────────────────────────────────────────

_orchestrator: Optional[IntelligenceOrchestrator] = None


def get_intelligence_orchestrator() -> IntelligenceOrchestrator:
    """Get or create the singleton IntelligenceOrchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IntelligenceOrchestrator()
    return _orchestrator
