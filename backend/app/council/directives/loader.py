"""DirectiveLoader — loads trading directives from markdown files.

Like CLAUDE.md but for trading rules. Agents load regime-specific
directives at runtime to adjust their behavior. Supports global directives
plus regime-specific overlays; thresholds are discoverable and testable.

Usage:
    from app.council.directives.loader import directive_loader
    text = directive_loader.load("bullish")
    threshold = directive_loader.get_threshold("VIX spike threshold")
    merged = directive_loader.get_directives_merged(regime="BULLISH")
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Directives directory at repo root
_DIRECTIVES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "directives"

# Map: (directive display name in markdown, config_key, is_percentage)
# Used to parse "## Section" / "- Display name: 35" or "- Display name: 3%" into config dict.
_DIRECTIVE_LINE_MAP: List[Tuple[str, str, bool]] = [
    ("VIX spike threshold", "cb_vix_spike_threshold", False),
    ("Daily drawdown limit", "cb_daily_drawdown_limit", True),
    ("Flash crash threshold", "cb_flash_crash_threshold", True),  # e.g. "5% in 5min" -> 0.05
    ("Max positions", "cb_max_positions", False),
    ("Max single position", "cb_max_single_position_pct", True),
    ("Hypothesis buy threshold", "llm_buy_confidence_threshold", False),
    ("Hypothesis sell threshold", "llm_sell_confidence_threshold", False),
    ("Arbiter minimum confidence", "arbiter_min_confidence", False),
    ("Strategy buy pass rate", "strategy_buy_pass_rate", False),
    ("Strategy sell pass rate", "strategy_sell_pass_rate", False),
    ("Maximum portfolio heat", "max_portfolio_heat", True),  # 6% -> 0.06
    ("Maximum single position", "max_single_position", True),  # 2% -> 0.02
    ("Minimum volume", "min_volume_threshold", False),  # 50,000 -> 50000
]

# Regime name normalization map
_REGIME_MAP = {
    "bullish": "regime_bull",
    "bull": "regime_bull",
    "trending_up": "regime_bull",
    "risk_on": "regime_bull",
    "bearish": "regime_bear",
    "bear": "regime_bear",
    "trending_down": "regime_bear",
    "risk_off": "regime_bear",
}


class DirectiveLoader:
    """Loads and caches trading directive markdown files."""

    def __init__(self, directives_dir: Optional[Path] = None):
        self._dir = directives_dir or _DIRECTIVES_DIR
        self._cache: Dict[str, str] = {}

    def _read_file(self, name: str) -> str:
        """Read a directive file by name (without .md extension)."""
        if name in self._cache:
            return self._cache[name]

        path = self._dir / f"{name}.md"
        if not path.exists():
            logger.debug("Directive file not found: %s", path)
            return ""

        content = path.read_text(encoding="utf-8")
        self._cache[name] = content
        return content

    def load(self, regime: str = "unknown") -> str:
        """Load global.md + regime-specific directives. Returns combined text.

        Args:
            regime: Current market regime (e.g., "bullish", "bearish", "choppy")

        Returns:
            Combined directive text (global + regime-specific)
        """
        parts = []

        # Always load global directives
        global_text = self._read_file("global")
        if global_text:
            parts.append(global_text)

        # Load regime-specific directives
        regime_key = _REGIME_MAP.get(regime.lower(), "")
        if regime_key:
            regime_text = self._read_file(regime_key)
            if regime_text:
                parts.append(regime_text)

        return "\n\n---\n\n".join(parts) if parts else ""

    def get_threshold(self, key: str) -> Optional[float]:
        """Parse a threshold value from global directives.

        Looks for patterns like "- Key name: 35" or "- Key name: 3%"

        Args:
            key: The threshold name to search for (case-insensitive)

        Returns:
            Float value if found, None otherwise
        """
        global_text = self._read_file("global")
        if not global_text:
            return None

        # Search for "- key: value" pattern (value may have trailing % or " in 5min" etc.)
        pattern = re.compile(
            rf"^-\s*{re.escape(key)}\s*:\s*([\d.,]+)(%?)",
            re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(global_text)
        if match:
            raw = match.group(1).replace(",", "")
            value = float(raw)
            if match.group(2) == "%":
                value /= 100.0  # Convert percentage
            return value
        return None

    def _parse_directives_text_to_dict(self, text: str) -> Dict[str, Any]:
        """Parse directive markdown text into config_key -> value dict.

        Scans for lines like "- Display name: 35" or "- Display name: 3%".
        Uses _DIRECTIVE_LINE_MAP to map display names to config keys.
        Numbers may contain commas (e.g. 50,000).
        """
        result: Dict[str, Any] = {}
        for display_name, config_key, is_pct in _DIRECTIVE_LINE_MAP:
            # Match "- Display name: number" or "number%" (number may have commas; allow trailing text e.g. "5% in 5min")
            pattern = re.compile(
                rf"^-\s*{re.escape(display_name)}\s*:\s*([\d.,]+)(%?)",
                re.MULTILINE | re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                raw = match.group(1).replace(",", "")
                value = float(raw)
                if is_pct or (match.group(2) == "%"):
                    value /= 100.0
                result[config_key] = value
        return result

    def get_directives_merged(self, regime: Optional[str] = None) -> Dict[str, Any]:
        """Load global + regime overlay and return merged threshold/config dict.

        Global directives are loaded first, then regime-specific file (if any)
        overlays. So regime values override global. Keys are internal config
        keys (e.g. cb_vix_spike_threshold) suitable for agent_config and
        circuit breaker.

        Args:
            regime: Market regime for overlay (e.g. "BULLISH", "BEARISH", "NEUTRAL").

        Returns:
            Dict of config_key -> value (floats/ints). Empty dict if no files.
        """
        combined: Dict[str, Any] = {}
        global_text = self._read_file("global")
        if global_text:
            combined.update(self._parse_directives_text_to_dict(global_text))

        if regime:
            regime_key = _REGIME_MAP.get(regime.lower(), "")
            if regime_key:
                regime_text = self._read_file(regime_key)
                if regime_text:
                    overlay = self._parse_directives_text_to_dict(regime_text)
                    for k, v in overlay.items():
                        combined[k] = v
        return combined

    def get_regime_bias(self, regime: str) -> str:
        """Extract the default bias from regime directives.

        Returns "LONG", "DEFENSIVE", or "NEUTRAL".
        """
        regime_key = _REGIME_MAP.get(regime.lower(), "")
        if not regime_key:
            return "NEUTRAL"

        text = self._read_file(regime_key)
        if not text:
            return "NEUTRAL"

        match = re.search(r"Default bias:\s*(\w+)", text, re.IGNORECASE)
        return match.group(1).upper() if match else "NEUTRAL"

    def clear_cache(self):
        """Clear cached directive files (for hot-reloading)."""
        self._cache.clear()


# Global singleton
directive_loader = DirectiveLoader()
