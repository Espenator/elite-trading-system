#!/usr/bin/env python3
"""
Position Sizer for OpenClaw v2.0
Risk-based position sizing with signal quality adjustments.

v2.0 Changes:
    - Queries REAL Alpaca account equity (no more hardcoded $100K)
    - Account equity cached for 5 minutes to avoid API spam
    - Calculates share quantity based on risk per trade
    - ATR-based stop loss distance
    - Signal quality adjustments (score-based scaling)
    - Max position limits per regime
    - Daily loss budget tracking

Integrates with config.py for risk parameters.
"""
import os
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Default risk parameters (overridden by config.py)
DEFAULT_RISK_PCT = float(os.getenv('DEFAULT_RISK_PCT', '1.5'))
MAX_DAILY_LOSS_PCT = float(os.getenv('MAX_DAILY_LOSS_PCT', '2.0'))

# Regime-based position limits
REGIME_LIMITS = {
    'GREEN': {'max_positions': 6, 'risk_pct': 2.0, 'scale': 1.0},
    'YELLOW': {'max_positions': 4, 'risk_pct': 1.5, 'scale': 0.75},
    'RED': {'max_positions': 0, 'risk_pct': 0.0, 'scale': 0.0},
    'RED_RECOVERY': {'max_positions': 3, 'risk_pct': 1.0, 'scale': 0.5},
}

# Score-based scaling factors
SCORE_SCALES = {
    'SLAM': 1.5,            # 90+ score: full + 50% bonus
    'HIGH_CONVICTION': 1.2, # 80+: full + 20%
    'TRADEABLE': 1.0,       # 70+: standard size
    'WATCHLIST': 0.5,       # 50+: half size
    'NO_TRADE': 0.0,        # Below 50: no trade
}

# ========== ACCOUNT EQUITY CACHE ==========
_equity_cache = {'value': None, 'timestamp': 0}
EQUITY_CACHE_TTL = 300  # 5 minutes


def get_alpaca_equity() -> float:
    """
    Fetch REAL account equity from Alpaca API.
    Cached for 5 minutes to avoid API rate limits.
    Falls back to $100K default if API fails.
    """
    now = time.time()
    if (_equity_cache['value'] is not None and
            now - _equity_cache['timestamp'] < EQUITY_CACHE_TTL):
        return _equity_cache['value']

    try:
        from alpaca.trading.client import TradingClient
        api_key = os.getenv('ALPACA_API_KEY', '')
        secret_key = os.getenv('ALPACA_SECRET_KEY', '')
        if not api_key or not secret_key:
            logger.warning("No Alpaca credentials, using default equity $100K")
            return 100000.0

        client = TradingClient(api_key, secret_key, paper=True)
        account = client.get_account()
        equity = float(account.equity)
        _equity_cache['value'] = equity
        _equity_cache['timestamp'] = now
        logger.info(f"Alpaca equity fetched: ${equity:,.2f}")
        return equity
    except Exception as e:
        logger.error(f"Failed to fetch Alpaca equity: {e}")
        if _equity_cache['value'] is not None:
            logger.info(f"Using cached equity: ${_equity_cache['value']:,.2f}")
            return _equity_cache['value']
        logger.warning("Using default equity $100,000")
        return 100000.0


class PositionSizer:
    """
    Calculates position sizes based on:
    - REAL account equity from Alpaca (cached)
    - Risk per trade (ATR-based stop)
    - Signal quality (composite score tier)
    - Market regime adjustments
    - Daily loss budget remaining
    """

    def __init__(self, account_equity: float = None,
                 regime: str = 'GREEN',
                 daily_loss_used: float = 0.0):
        # v2.0: Query real equity if not provided
        if account_equity is None:
            self.account_equity = get_alpaca_equity()
        else:
            self.account_equity = account_equity
        self.regime = regime
        self.daily_loss_used = daily_loss_used
        self.regime_config = REGIME_LIMITS.get(regime, REGIME_LIMITS['YELLOW'])

    def calculate(self, price: float, atr: float,
                  score_tier: str = 'TRADEABLE',
                  stop_atr_multiple: float = 1.5,
                  custom_stop: Optional[float] = None) -> Dict:
        """
        Calculate position size for a trade.

        Args:
            price: Current stock price
            atr: Average True Range
            score_tier: From CompositeScorer (SLAM/HIGH/TRADEABLE/etc)
            stop_atr_multiple: ATR multiplier for stop distance
            custom_stop: Override stop price (ignores ATR calc)

        Returns:
            Dict with shares, dollar_risk, stop_price, targets, etc.
        """
        # Check regime allows trading
        if self.regime_config['risk_pct'] == 0:
            return self._no_trade_result(price, 'RED_REGIME')

        # Check score tier allows trading
        score_scale = SCORE_SCALES.get(score_tier, 0)
        if score_scale == 0:
            return self._no_trade_result(price, 'LOW_SCORE')

        # Calculate stop distance
        if custom_stop and custom_stop > 0:
            stop_distance = abs(price - custom_stop)
            stop_price = custom_stop
        else:
            stop_distance = atr * stop_atr_multiple
            stop_price = price - stop_distance

        if stop_distance <= 0:
            return self._no_trade_result(price, 'INVALID_STOP')

        # Base risk amount
        risk_pct = self.regime_config['risk_pct'] / 100
        base_risk = self.account_equity * risk_pct

        # Apply score scaling
        regime_scale = self.regime_config['scale']
        adjusted_risk = base_risk * score_scale * regime_scale

        # Check daily loss budget
        daily_budget = self.account_equity * (MAX_DAILY_LOSS_PCT / 100)
        remaining_budget = daily_budget - self.daily_loss_used
        if remaining_budget <= 0:
            return self._no_trade_result(price, 'DAILY_LIMIT')

        adjusted_risk = min(adjusted_risk, remaining_budget)

        # Calculate shares
        shares = int(adjusted_risk / stop_distance)
        if shares <= 0:
            return self._no_trade_result(price, 'ZERO_SHARES')

        # Position value check (max 20% of equity in one position)
        max_position = self.account_equity * 0.20
        if shares * price > max_position:
            shares = int(max_position / price)

        dollar_risk = shares * stop_distance
        position_value = shares * price

        # Calculate targets
        target_1 = price + stop_distance       # 1:1 R:R
        target_2 = price + (stop_distance * 2) # 2:1 R:R
        target_3 = price + (stop_distance * 3) # 3:1 R:R

        result = {
            'shares': shares,
            'price': round(price, 2),
            'stop_price': round(stop_price, 2),
            'stop_distance': round(stop_distance, 2),
            'dollar_risk': round(dollar_risk, 2),
            'risk_pct_actual': round((dollar_risk / self.account_equity) * 100, 2),
            'position_value': round(position_value, 2),
            'position_pct': round((position_value / self.account_equity) * 100, 2),
            'target_1': round(target_1, 2),
            'target_2': round(target_2, 2),
            'target_3': round(target_3, 2),
            'score_tier': score_tier,
            'score_scale': score_scale,
            'regime': self.regime,
            'regime_scale': regime_scale,
            'atr': round(atr, 2),
            'account_equity': round(self.account_equity, 2),
            'can_trade': True,
            'reason': 'OK',
        }

        logger.info(f"Position: {shares} shares @ ${price:.2f}, "
                    f"stop ${stop_price:.2f}, risk ${dollar_risk:.2f} "
                    f"({result['risk_pct_actual']:.1f}%) "
                    f"[equity=${self.account_equity:,.0f}]")
        return result

    def _no_trade_result(self, price: float, reason: str) -> Dict:
        """Return a no-trade result with reason."""
        logger.warning(f"No trade: {reason} @ ${price:.2f}")
        return {
            'shares': 0,
            'price': round(price, 2),
            'stop_price': 0,
            'stop_distance': 0,
            'dollar_risk': 0,
            'risk_pct_actual': 0,
            'position_value': 0,
            'position_pct': 0,
            'target_1': 0,
            'target_2': 0,
            'target_3': 0,
            'can_trade': False,
            'reason': reason,
        }

    def format_order_summary(self, sizing: Dict) -> str:
        """Format sizing for Slack display."""
        if not sizing.get('can_trade'):
            return f":no_entry: No trade: {sizing.get('reason', 'unknown')}"

        return (
            f":moneybag: *Position Size*\n"
            f"  Shares: {sizing['shares']} @ ${sizing['price']:.2f}\n"
            f"  Stop: ${sizing['stop_price']:.2f} (-${sizing['stop_distance']:.2f})\n"
            f"  Risk: ${sizing['dollar_risk']:.2f} ({sizing['risk_pct_actual']:.1f}%)\n"
            f"  T1: ${sizing['target_1']:.2f} (1:1)\n"
            f"  T2: ${sizing['target_2']:.2f} (2:1)\n"
            f"  T3: ${sizing['target_3']:.2f} (3:1)\n"
            f"  Account: ${sizing.get('account_equity', 0):,.0f}"
        )


# ========== MODULE-LEVEL CONVENIENCE ==========
def calculate_position(price: float, atr: float,
                      score_tier: str = 'TRADEABLE',
                      account_equity: float = None,
                      regime: str = 'GREEN') -> Dict:
    """Convenience function for pipeline use. Uses real equity by default."""
    sizer = PositionSizer(account_equity=account_equity, regime=regime)
    return sizer.calculate(price=price, atr=atr, score_tier=score_tier)


def calculate_position_size(ticker: str = '', price: float = 0,
                           atr: float = 0, composite_score: int = 50,
                           account_equity: float = None,
                           regime: str = 'GREEN') -> Dict:
    """Alias for main.py compatibility. Maps composite_score to score_tier."""
    if composite_score >= 90:
        score_tier = 'SLAM'
    elif composite_score >= 80:
        score_tier = 'HIGH_CONVICTION'
    elif composite_score >= 70:
        score_tier = 'TRADEABLE'
    elif composite_score >= 50:
        score_tier = 'WATCHLIST'
    else:
        score_tier = 'NO_TRADE'
    return calculate_position(price=price, atr=atr, score_tier=score_tier,
                              account_equity=account_equity, regime=regime)
