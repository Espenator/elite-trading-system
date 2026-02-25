import logging
from config import REGIME_CONFIG, REGIME_GREEN_VIX, REGIME_YELLOW_VIX, REGIME_RED_VIX, VELEZ_SLAM, VELEZ_GO, VELEZ_WATCH
from config import CRASH_HY_SPREAD, CRASH_VIX_SINGLE_DAY, CRASH_BREADTH_MIN, CRASH_SPY_DROP, CRASH_VIX_SPIKE
from macro_context import macro_context

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Market Regime Detection System:
    - GREEN: Momentum/trending strategies (reversion=0.30, risk_pct=2.0, max_positions=6)
    - YELLOW: Cautious/balanced (reversion=0.60, risk_pct=1.5, max_positions=5)
    - RED: Mean reversion/defensive (reversion=0.0, risk_pct=0.0, max_positions=0)
    - RED_RECOVERY: Recovery from crash (reversion=1.0, risk_pct=1.0, max_positions=4)

    Now uses macro_context.py (FRED API) for real VIX and HY spread data.
    """

    def __init__(self):
        self.current_regime = "YELLOW"  # Default to cautious
        self.vix = None
        self.velez_score = None
        self.crash_detected = False
        self._macro = macro_context  # FRED-backed macro data

    def get_vix(self):
        """Fetch current VIX from FRED via macro_context (with Yahoo fallback)."""
        try:
            vix = self._macro.get_vix()
            self.vix = vix
            logger.debug(f"VIX fetched: {vix:.1f}")
            return vix
        except Exception as e:
            logger.error(f"Error fetching VIX: {e}")
            return self.vix if self.vix else 18.0

    def calculate_velez_score(self):
        """
        Calculate VELEZ score from market breadth.
        Uses macro_context breadth proxy (yield-curve derived) when
        a real breadth scanner is not connected.
        """
        try:
            if self.velez_score is not None:
                return self.velez_score
            # Use breadth proxy from macro_context (yield curve normalized 0-1)
            breadth_proxy = self._macro.get_breadth_proxy()
            # Scale to VELEZ range (0-100)
            velez = round(breadth_proxy * 100)
            logger.debug(f"VELEZ breadth proxy: {velez}")
            return velez
        except Exception as e:
            logger.error(f"Error calculating VELEZ: {e}")
            return 60

    def detect_crash(self):
        """
        Detect crash protocol triggers using real FRED macro data.
        Checks: VIX spike, HY spread, yield curve inversion.
        """
        try:
            vix = self.get_vix()
            hy_spread_bps = self._macro.get_hy_spread()

            crash = False

            # Primary crash signals
            if vix > CRASH_VIX_SINGLE_DAY:  # Config: 25
                logger.warning(f"CRASH SIGNAL: VIX={vix:.1f} > {CRASH_VIX_SINGLE_DAY}")
                crash = True

            if hy_spread_bps > CRASH_HY_SPREAD * 10000:  # Config: 0.15 (scaled to bps)
                logger.warning(f"CRASH SIGNAL: HY spread={hy_spread_bps:.0f}bps")
                crash = True

            # Hard threshold: VIX > 40 = extreme fear
            if vix > 40:
                logger.warning(f"EXTREME FEAR: VIX={vix:.1f}")
                crash = True

            # Yield curve inversion check
            yield_curve = self._macro.get_yield_curve()
            if yield_curve < -0.5:
                logger.info(f"Yield curve deeply inverted: {yield_curve:.2f}% (recession risk)")

            self.crash_detected = crash
            return crash

        except Exception as e:
            logger.error(f"Error in crash detection: {e}")
            return False

    def get_regime(self):
        """Determine current market regime using real macro data."""
        vix = self.get_vix()
        velez = self.calculate_velez_score()

        # Check for crash first
        if self.detect_crash():
            self.current_regime = "RED"
            return "RED", REGIME_CONFIG["RED"]

        # VIX-based regime thresholds
        if vix <= REGIME_GREEN_VIX:
            if velez >= VELEZ_SLAM:
                self.current_regime = "GREEN"
                return "GREEN", REGIME_CONFIG["GREEN"]

        if vix <= REGIME_YELLOW_VIX:
            if velez >= VELEZ_GO:
                self.current_regime = "YELLOW"
                return "YELLOW", REGIME_CONFIG["YELLOW"]

        # Default to RED if conditions not met
        self.current_regime = "RED"
        return "RED", REGIME_CONFIG["RED"]

    def get_regime_summary(self):
        """Get human-readable regime summary with real macro data."""
        regime, config = self.get_regime()
        vix = self.get_vix()
        velez = self.calculate_velez_score()
        hy_spread = self._macro.get_hy_spread()
        yield_curve = self._macro.get_yield_curve()

        summary = f"""📊 **MARKET REGIME: {regime}**
🎯 **Macro Indicators (FRED Live):**
• VIX: {vix:.1f}
• VELEZ Score: {velez}%
• HY Spread: {hy_spread:.0f} bps
• Yield Curve (10Y-2Y): {yield_curve:+.2f}%
• Crash Protocol: {'🚨 ACTIVE' if self.crash_detected else '✅ Clear'}
⚙️ **Trading Parameters:**
• Momentum: {config['momentum']:.0%}
• Mean Reversion: {config['reversion']:.0%}
• Risk per Trade: {config['risk_pct']:.1f}%
• Max Positions: {config['max_positions']}
💡 **Strategy:** {self._get_strategy_description(regime)}
"""
        return summary

    def _get_strategy_description(self, regime):
        """Get strategy description for regime."""
        descriptions = {
            "GREEN": "Aggressive momentum trades, trend following, full position sizing",
            "YELLOW": "Balanced approach, selective trades, moderate sizing",
            "RED": "🛑 NO NEW TRADES - Wait for market stabilization",
            "RED_RECOVERY": "Mean reversion only, small position sizes, cautious re-entry"
        }
        return descriptions.get(regime, "Unknown regime")


# Singleton instance
regime_detector = RegimeDetector()
