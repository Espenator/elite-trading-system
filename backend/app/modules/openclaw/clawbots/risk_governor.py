# Risk Governor for Clawbots Trading System

# Enforces position sizing, exposure limits, stop losses, daily limits, etc.
# Based on OpenClaw Trading Intelligence rules.

import math

class RiskGovernor:
    """
    Risk management class for Clawbots auto-trading.
    Handles position sizing, exposure checks, order generation.
    """

    def __init__(self, account_size=100000.0,
                 max_per_trade_pct=0.05,
                 max_exposure_pct=0.60,
                 stop_loss_pct=0.015,
                 max_daily_trades=5):
        self.account_size = account_size
        self.max_per_trade_pct = max_per_trade_pct
        self.max_per_trade = account_size * max_per_trade_pct
        self.max_exposure_pct = max_exposure_pct
        self.max_exposure = account_size * max_exposure_pct
        self.stop_loss_pct = stop_loss_pct
        self.max_daily_trades = max_daily_trades
        self.daily_trades_count = 0
        self.current_exposure = 0.0  # Update from broker API (e.g., Alpaca)
        self.grade_size_multipliers = {
            'A+': 1.0,  # 5%
            'A': 0.8,   # 4%
            'B+': 0.6   # 3%
        }

    def update_daily_trades(self, count):
        """Update daily trade count."""
        self.daily_trades_count = count

    def update_exposure(self, exposure):
        """Update current total exposure."""
        self.current_exposure = exposure

    def calculate_shares(self, entry_price, grade='A', conviction_multiplier=1.0):
        """Calculate shares based on grade and conviction."""
        base_pct = self.max_per_trade_pct * self.grade_size_multipliers.get(grade, 0.8)
        alloc = self.account_size * base_pct * conviction_multiplier
        shares = math.floor(alloc / entry_price)
        return shares

    def can_execute_trade(self, entry_price, grade='A', conviction_multiplier=1.0):
        """Check if trade can be executed per risk rules."""
        if self.daily_trades_count >= self.max_daily_trades:
            return False, 'Daily trade limit reached.'

        shares = self.calculate_shares(entry_price, grade, conviction_multiplier)
        proposed_value = shares * entry_price

        if proposed_value > self.max_per_trade:
            return False, 'Exceeds max per trade size.'

        if self.current_exposure + proposed_value > self.max_exposure:
            return False, f'Exceeds max exposure: {self.current_exposure + proposed_value:.0f} > {self.max_exposure:.0f}'

        return True, 'Approved'

    def generate_trade_order(self, ticker, entry_price, grade='A', conviction_multiplier=1.0,
                             target1_rr=2.0, target2_rr=4.0):
        """Generate full order params with stops and targets."""
        can_trade, reason = self.can_execute_trade(entry_price, grade, conviction_multiplier)
        if not can_trade:
            return None, reason

        shares = self.calculate_shares(entry_price, grade, conviction_multiplier)
        stop_price = entry_price * (1 - self.stop_loss_pct)
        risk_per_share = entry_price - stop_price

        target1_price = entry_price + (target1_rr * risk_per_share)
        target2_price = entry_price + (target2_rr * risk_per_share)

        rr1 = (target1_price - entry_price) / risk_per_share
        rr2 = (target2_price - entry_price) / risk_per_share

        if rr1 < 2.0:
            return None, 'Risk/Reward ratio too low (min 2:1).'

        order = {
            'ticker': ticker,
            'type': 'long',  # Assume long for now
            'shares': shares,
            'entry_price': entry_price,
            'stop_price': stop_price,
            'target1_price': target1_price,
            'target2_price': target2_price,
            'rr1': round(rr1, 2),
            'rr2': round(rr2, 2),
            'notional_value': round(shares * entry_price, 2),
            'risk_amount': round(shares * risk_per_share, 2),
            'conviction_multiplier': conviction_multiplier
        }

        return order, 'Order generated successfully.'


# Example usage and testing
if __name__ == '__main__':
    governor = RiskGovernor(account_size=100000)

    # Golden Window example: A+ trade
    order, msg = governor.generate_trade_order('AAPL', 220.0, grade='A+', conviction_multiplier=1.2)
    print('AAPL Order:', order)
    print(msg)

    # Update exposure simulation
    governor.update_exposure(50000)
    order2, msg2 = governor.generate_trade_order('TSLA', 250.0, grade='A')
    print('\nTSLA Order:', order2)
    print(msg2)