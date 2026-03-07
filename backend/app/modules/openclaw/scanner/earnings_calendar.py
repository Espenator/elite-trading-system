"""
Earnings Calendar Scanner - Embodier Trader
Replaces yfinance earnings lookups with Finviz + SEC EDGAR.
Uses finviz_service.py (already in stack) for earnings date data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

try:
    from backend.app.services.finviz_service import FinvizService
except ImportError:
    try:
        from app.services.finviz_service import FinvizService
    except ImportError:
        FinvizService = None

try:
    from backend.app.services.sec_edgar_service import SECEdgarService
except ImportError:
    try:
        from app.services.sec_edgar_service import SECEdgarService
    except ImportError:
        SECEdgarService = None

logger = logging.getLogger(__name__)

# ========== EARNINGS CONFIG ==========
EARNINGS_BLOCK_DAYS = 3      # Block entries within 3 days before earnings
EARNINGS_WARNING_DAYS = 7    # Warn within 7 days
EARNINGS_PENALTY_SCORE = -10 # Score penalty for earnings proximity


class EarningsCalendar:
    """
    Scans for upcoming earnings dates using Finviz screener data
    and SEC EDGAR filings. No yfinance dependency.
    """

    def __init__(self):
        self.finviz = FinvizService() if FinvizService else None
        self.edgar = SECEdgarService() if SECEdgarService else None
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = timedelta(hours=4)
        self._cache_timestamps: Dict[str, datetime] = {}

    def _is_cache_valid(self, symbol: str) -> bool:
        if symbol not in self._cache_timestamps:
            return False
        return datetime.now() - self._cache_timestamps[symbol] < self._cache_ttl

    def get_earnings_date(self, symbol: str) -> Optional[datetime]:
        """
        Get next earnings date for a symbol.
        Primary: Finviz screener 'Earnings Date' field.
        Fallback: SEC EDGAR 10-Q/10-K filing pattern estimation.

        Returns datetime of next earnings or None if unavailable.
        """
        if self._is_cache_valid(symbol):
            cached = self._cache.get(symbol, {})
            if cached.get("earnings_date"):
                return cached["earnings_date"]

        earnings_date = self._fetch_from_finviz(symbol)

        if earnings_date is None:
            earnings_date = self._estimate_from_edgar(symbol)

        if earnings_date:
            self._cache[symbol] = {"earnings_date": earnings_date}
            self._cache_timestamps[symbol] = datetime.now()

        return earnings_date

    def _fetch_from_finviz(self, symbol: str) -> Optional[datetime]:
        """
        Finviz screener results include 'Earnings Date' field.
        Format is typically 'MMM DD' or 'MMM DD AMC/BMO'.
        """
        if not self.finviz:
            return None
        try:
            stock_data = self.finviz.get_stock_data(symbol)
            if not stock_data:
                return None

            earnings_str = stock_data.get("Earnings Date") or stock_data.get("earnings_date")
            if not earnings_str:
                return None

            earnings_str = earnings_str.strip()
            # Strip AMC (After Market Close) / BMO (Before Market Open) suffixes
            for suffix in [" AMC", " BMO", " AH", " BM"]:
                earnings_str = earnings_str.replace(suffix, "")
            earnings_str = earnings_str.strip()

            # Parse common Finviz date formats
            for fmt in ["%b %d", "%b %d %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                try:
                    parsed = datetime.strptime(earnings_str, fmt)
                    # If no year was in the format, assign current or next year
                    if parsed.year == 1900:
                        now = datetime.now()
                        parsed = parsed.replace(year=now.year)
                        if parsed < now - timedelta(days=30):
                            parsed = parsed.replace(year=now.year + 1)
                    return parsed
                except ValueError:
                    continue

            logger.warning(f"Could not parse Finviz earnings date '{earnings_str}' for {symbol}")
            return None

        except Exception as e:
            logger.debug(f"Finviz earnings lookup failed for {symbol}: {e}")
            return None

    def _estimate_from_edgar(self, symbol: str) -> Optional[datetime]:
        """
        Fallback: Use SEC EDGAR filing history to estimate next earnings.
        Companies report quarterly ~same time each year.
        """
        if not self.edgar:
            return None
        try:
            filings = self.edgar.get_recent_filings(symbol, form_type="10-Q", count=4)
            if not filings or len(filings) < 2:
                return None

            filing_dates = []
            for f in filings:
                date_str = f.get("filed") or f.get("filedAt") or f.get("date")
                if date_str:
                    try:
                        filing_dates.append(datetime.strptime(date_str[:10], "%Y-%m-%d"))
                    except ValueError:
                        continue

            if len(filing_dates) < 2:
                return None

            filing_dates.sort(reverse=True)

            # Average gap between filings (~90 days for quarterly)
            gaps = []
            for i in range(len(filing_dates) - 1):
                gap = (filing_dates[i] - filing_dates[i + 1]).days
                if 60 < gap < 120:  # sanity check for quarterly
                    gaps.append(gap)

            if not gaps:
                return None

            avg_gap = sum(gaps) // len(gaps)
            estimated_next = filing_dates[0] + timedelta(days=avg_gap)

            # Only return if it's in the future
            if estimated_next > datetime.now():
                logger.info(f"Estimated next earnings for {symbol}: {estimated_next.date()} (from EDGAR)")
                return estimated_next
            return None

        except Exception as e:
            logger.debug(f"EDGAR earnings estimation failed for {symbol}: {e}")
            return None

    def get_next_earnings(self, symbol: str) -> Optional[Dict]:
        """Get next earnings date for a symbol (backward-compatible wrapper)."""
        earnings_date = self.get_earnings_date(symbol)
        if not earnings_date:
            return {
                "symbol": symbol,
                "earnings_date": None,
                "days_until": 999,
                "fetched_at": datetime.now(),
                "source": "none",
            }

        now = datetime.now()
        days_until = (earnings_date.date() - now.date()).days
        source = "finviz"
        # Check if from EDGAR fallback
        if not self.finviz:
            source = "edgar_estimate"

        return {
            "symbol": symbol,
            "earnings_date": earnings_date.strftime("%Y-%m-%d"),
            "days_until": days_until,
            "fetched_at": now,
            "source": source,
        }

    def check_earnings_safety(self, symbol: str) -> Dict:
        """Check if it's safe to enter a trade based on earnings proximity."""
        earnings = self.get_next_earnings(symbol)
        if not earnings:
            return {"safe": True, "reason": "No earnings data", "penalty": 0}

        days = earnings.get("days_until", 999)
        earnings_date = earnings.get("earnings_date", "unknown")

        if days <= EARNINGS_BLOCK_DAYS:
            return {
                "safe": False,
                "reason": f"BLOCKED: Earnings in {days} days ({earnings_date})",
                "days_until": days,
                "earnings_date": earnings_date,
                "penalty": EARNINGS_PENALTY_SCORE,
            }
        elif days <= EARNINGS_WARNING_DAYS:
            return {
                "safe": True,
                "reason": f"WARNING: Earnings in {days} days ({earnings_date})",
                "days_until": days,
                "earnings_date": earnings_date,
                "penalty": EARNINGS_PENALTY_SCORE // 2,
            }
        else:
            return {
                "safe": True,
                "reason": f"Clear: Earnings in {days}+ days",
                "days_until": days,
                "earnings_date": earnings_date,
                "penalty": 0,
            }

    def batch_check(self, symbols: List[str]) -> Dict[str, Dict]:
        """Check earnings safety for multiple symbols."""
        results = {}
        for symbol in symbols:
            results[symbol] = self.check_earnings_safety(symbol)
        return results

    def filter_safe_candidates(self, symbols: List[str]) -> List[str]:
        """Filter out candidates too close to earnings."""
        safe = []
        for symbol in symbols:
            check = self.check_earnings_safety(symbol)
            if check["safe"]:
                safe.append(symbol)
            else:
                logger.info(f"Earnings filter removed {symbol}: {check['reason']}")
        return safe

    def get_upcoming_earnings(
        self, symbols: List[str], days_ahead: int = 14
    ) -> List[Dict]:
        """
        Scan a list of symbols and return those with earnings
        in the next N days. Sorted by date ascending.
        """
        cutoff = datetime.now() + timedelta(days=days_ahead)
        results = []

        for symbol in symbols:
            try:
                earnings_date = self.get_earnings_date(symbol)
                if earnings_date and datetime.now() <= earnings_date <= cutoff:
                    results.append({
                        "symbol": symbol,
                        "earnings_date": earnings_date.isoformat(),
                        "days_until": (earnings_date - datetime.now()).days,
                        "source": "finviz" if self.finviz else "edgar_estimate",
                    })
            except Exception as e:
                logger.debug(f"Earnings scan failed for {symbol}: {e}")
                continue

        results.sort(key=lambda x: x["days_until"])
        return results

    def is_near_earnings(self, symbol: str, days_threshold: int = 3) -> bool:
        """
        Returns True if the symbol has earnings within N days.
        Used by risk_governor to flag pre-earnings risk.
        """
        earnings_date = self.get_earnings_date(symbol)
        if not earnings_date:
            return False
        days_until = (earnings_date - datetime.now()).days
        return 0 <= days_until <= days_threshold

    def format_earnings_alert(self, check: Dict) -> str:
        """Format earnings check for Slack."""
        symbol = check.get("symbol", "???")
        days = check.get("days_until", 999)

        if days <= EARNINGS_BLOCK_DAYS:
            return f"\U0001f6d1 *{symbol}*: {check.get('reason', '')}"
        elif days <= EARNINGS_WARNING_DAYS:
            return f"\u26a0\ufe0f *{symbol}*: {check.get('reason', '')}"
        return ""

    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached earnings data for a symbol or all."""
        if symbol:
            self._cache.pop(symbol, None)
            self._cache_timestamps.pop(symbol, None)
        else:
            self._cache.clear()
            self._cache_timestamps.clear()


# ========== MODULE-LEVEL CONVENIENCE ==========

def check_earnings(symbol: str) -> Dict:
    """Check earnings safety for a single symbol."""
    cal = EarningsCalendar()
    return cal.check_earnings_safety(symbol)


def filter_by_earnings(symbols: List[str]) -> List[str]:
    """Filter symbols to only those safe from earnings."""
    cal = EarningsCalendar()
    return cal.filter_safe_candidates(symbols)


def get_earnings_penalties(symbols: List[str]) -> Dict[str, Dict]:
    """Get earnings safety data for list of symbols.

    Returns dict with blocked, penalty, reason, etc. for each symbol.
    Used by daily_scanner for earnings integration.
    """
    cal = EarningsCalendar()
    results = cal.batch_check(symbols)

    enriched = {}
    for sym, data in results.items():
        enriched[sym] = {
            "blocked": not data.get("safe", True),
            "penalty": data.get("penalty", 0),
            "reason": data.get("reason", ""),
            "days_until": data.get("days_until", 999),
            "earnings_date": data.get("earnings_date"),
            "safe": data.get("safe", True),
        }
    return enriched
