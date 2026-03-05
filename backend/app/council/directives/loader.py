"""DirectiveLoader — loads trading directives from markdown files.

Like CLAUDE.md but for trading rules. Agents load regime-specific
directives at runtime to adjust their behavior.

Usage:
    from app.council.directives.loader import directive_loader
    text = directive_loader.load("bullish")
    threshold = directive_loader.get_threshold("VIX spike threshold")
"""
import logging
import re
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Directives directory at repo root
_DIRECTIVES_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "directives"

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

        # Search for "- key: value" pattern
        pattern = re.compile(
            rf"^-\s*{re.escape(key)}\s*:\s*([\d.]+)(%?)",
            re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(global_text)
        if match:
            value = float(match.group(1))
            if match.group(2) == "%":
                value /= 100.0  # Convert percentage
            return value
        return None

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
