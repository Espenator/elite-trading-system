"""
Paper trading portfolio manager
Manages $1M paper account
"""

from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import yaml
from pathlib import Path

from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)

# Load config
config_path = Path(__file__).parent.parent / "config.yaml"
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

@dataclass
class Position:
    """Position data class"""
    symbol: str
    direction: str  # LONG or SHORT
    shares: int
    entry_price: float
    current_price: float
    stop_loss: float
    target_1: float
    target_2: float
    entry_time: datetime
    cost_basis: float
    unrealized_pnl: float = 0.0
    r_multiple: float = 0.0
    
    def update_price(self, current_price: float):
        """Update current price and calculate P&L"""
        self.current_price = current_price
        
        if self.direction == 'LONG':
            self.unrealized_pnl = (current_price - self.entry_price) * self.shares
            risk = (self.entry_price - self.stop_loss) * self.shares
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.shares
            risk = (self.stop_loss - self.entry_price) * self.shares
        
        if risk > 0:
            self.r_multiple = self.unrealized_pnl / risk
    
    def to_dict(self):
        """Convert to dictionary"""
        d = asdict(self)
        d['entry_time'] = self.entry_time.isoformat()
        return d

class PaperPortfolio:
    """
    Paper trading account manager
    """
    
    def __init__(self):
        self.initial_capital = config['account']['capital']
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history: List[Dict] = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        
        logger.info(f"Paper portfolio initialized: ${self.cash:,.0f}")
    
    def get_equity(self) -> float:
        """Calculate total equity (cash + positions)"""
        position_value = sum(p.cost_basis + p.unrealized_pnl for p in self.positions.values())
        return self.cash + position_value
    
    def get_available_cash(self) -> float:
        """Get available cash for new trades"""
        return self.cash
    
    def can_open_position(self, cost: float) -> bool:
        """Check if we have enough cash and position slots"""
        max_positions = config['account']['max_positions']
        
        if len(self.positions) >= max_positions:
            logger.warning(f"Max positions reached ({max_positions})")
            return False
        
        if cost > self.cash:
            logger.warning(f"Insufficient cash: ${self.cash:,.0f} < ${cost:,.0f}")
            return False
        
        return True
    
    def open_position(
        self,
        symbol: str,
        direction: str,
        shares: int,
        entry_price: float,
        stop_loss: float,
        target_1: float,
        target_2: float
    ) -> Optional[Position]:
        """
        Open a new position
        
        Returns:
            Position object if successful, None otherwise
        """
        cost = shares * entry_price
        
        if not self.can_open_position(cost):
            return None
        
        # Create position
        position = Position(
            symbol=symbol,
            direction=direction,
            shares=shares,
            entry_price=entry_price,
            current_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            entry_time=datetime.now(),
            cost_basis=cost
        )
        
        # Deduct cash
        self.cash -= cost
        
        # Add to positions
        self.positions[symbol] = position
        
        logger.info(f"✅ Position opened: {symbol} {direction} {shares} @ ${entry_price:.2f}")
        logger.info(f"   Stop: ${stop_loss:.2f} | T1: ${target_1:.2f} | T2: ${target_2:.2f}")
        logger.info(f"   Cash remaining: ${self.cash:,.0f}")
        
        # Publish event
        event_bus.publish('position_opened', position.to_dict())
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = 'Manual'
    ) -> Optional[Dict]:
        """
        Close a position
        
        Returns:
            Trade result dict if successful, None otherwise
        """
        if symbol not in self.positions:
            logger.warning(f"Position {symbol} not found")
            return None
        
        position = self.positions[symbol]
        
        # Calculate P&L
        if position.direction == 'LONG':
            pnl = (exit_price - position.entry_price) * position.shares
        else:  # SHORT
            pnl = (position.entry_price - exit_price) * position.shares
        
        # Calculate R-multiple
        if position.direction == 'LONG':
            risk = (position.entry_price - position.stop_loss) * position.shares
        else:
            risk = (position.stop_loss - position.entry_price) * position.shares
        
        r_multiple = pnl / risk if risk > 0 else 0
        
        # Return cash
        proceeds = position.shares * exit_price
        self.cash += proceeds
        
        # Update totals
        self.total_pnl += pnl
        self.daily_pnl += pnl
        
        # Create trade record
        trade = {
            'symbol': symbol,
            'direction': position.direction,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'shares': position.shares,
            'entry_time': position.entry_time.isoformat(),
            'exit_time': datetime.now().isoformat(),
            'pnl': pnl,
            'r_multiple': r_multiple,
            'reason': reason,
            'outcome': 'WIN' if pnl > 0 else 'LOSS'
        }
        
        self.trade_history.append(trade)
        
        # Remove position
        del self.positions[symbol]
        
        outcome = "🟢 WIN" if pnl > 0 else "🔴 LOSS"
        logger.info(f"{outcome} Position closed: {symbol} @ ${exit_price:.2f}")
        logger.info(f"   P&L: ${pnl:,.2f} ({r_multiple:.2f}R) | Reason: {reason}")
        logger.info(f"   Cash: ${self.cash:,.0f} | Total P&L: ${self.total_pnl:,.0f}")
        
        # Publish event
        event_bus.publish('position_closed', trade)
        
        return trade
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update a position's current price"""
        if symbol in self.positions:
            self.positions[symbol].update_price(current_price)
    
    def get_stats(self) -> Dict:
        """Get portfolio statistics"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_r_multiple': 0.0
            }
        
        wins = [t for t in self.trade_history if t['outcome'] == 'WIN']
        losses = [t for t in self.trade_history if t['outcome'] == 'LOSS']
        
        return {
            'initial_capital': self.initial_capital,
            'cash': self.cash,
            'equity': self.get_equity(),
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'return_pct': (self.get_equity() / self.initial_capital - 1) * 100,
            'total_trades': len(self.trade_history),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / len(self.trade_history) * 100 if self.trade_history else 0,
            'avg_r_multiple': sum(t['r_multiple'] for t in self.trade_history) / len(self.trade_history),
            'active_positions': len(self.positions)
        }

# Global portfolio instance
portfolio = PaperPortfolio()

def check_positions():
    """Check all positions for stop/target hits"""
    # This will be called every minute
    # TODO: Implement in next iteration
    pass
