"""
Backend Services - Elite Trading System
========================================

Business logic layer between API and database
Handles portfolio management, position tracking, and trade execution

Author: Elite Trading Team
Date: December 6, 2025
Version: 6.0 (Aurora)
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from backend.database.models import (
    ShadowPortfolio, Position, Trade, SignalHistory,
    SystemEvent, MacroRegime, HedgePosition, Prediction
)
from backend.database import get_db_session
from backend.core.logger import get_logger

logger = get_logger(__name__)

# ============================================================================
# PORTFOLIO SERVICES
# ============================================================================

def get_portfolio_summary() -> Dict:
    """Get shadow portfolio summary for Aurora dashboard"""
    with get_db_session() as session:
        portfolio = session.query(ShadowPortfolio).first()
        
        if not portfolio:
            raise ValueError("No shadow portfolio found")
        
        # Get active positions
        active_positions = session.query(Position).filter(
            Position.portfolio_id == portfolio.id,
            Position.is_active == True
        ).all()
        
        # Get recent trades
        recent_trades = session.query(Trade).filter(
            Trade.portfolio_id == portfolio.id
        ).order_by(Trade.exit_time.desc()).limit(10).all()
        
        return {
            "id": portfolio.id,
            "name": portfolio.name,
            "starting_balance": portfolio.starting_balance,
            "current_balance": portfolio.current_balance,
            "total_pnl": portfolio.total_pnl,
            "total_pnl_pct": portfolio.total_pnl_pct,
            "total_trades": portfolio.total_trades,
            "winning_trades": portfolio.winning_trades,
            "losing_trades": portfolio.losing_trades,
            "win_rate": portfolio.win_rate,
            "active_positions_count": len(active_positions),
            "recent_trades_count": len(recent_trades),
            "updated_at": portfolio.updated_at.isoformat()
        }


def get_active_positions_list() -> List[Dict]:
    """Get all active positions with current P&L"""
    with get_db_session() as session:
        portfolio = session.query(ShadowPortfolio).first()
        
        positions = session.query(Position).filter(
            Position.portfolio_id == portfolio.id,
            Position.is_active == True
        ).all()
        
        position_list = []
        for pos in positions:
            # Calculate time left (example: based on entry time)
            time_diff = datetime.utcnow() - pos.entry_time
            hours_elapsed = time_diff.total_seconds() / 3600
            time_left = f"{int(24 - hours_elapsed)}H" if hours_elapsed < 24 else "EXPIRED"
            
            position_list.append({
                "id": pos.id,
                "symbol": pos.symbol,
                "direction": pos.direction,
                "quantity": pos.quantity,
                "entry_price": pos.entry_price,
                "current_price": pos.current_price,
                "stop_price": pos.stop_price,
                "target_price": pos.target_price,
                "unrealized_pnl": pos.unrealized_pnl,
                "unrealized_pnl_pct": pos.unrealized_pnl_pct,
                "confidence": pos.confidence,
                "entry_time": pos.entry_time.isoformat(),
                "time_left": time_left
            })
        
        return position_list


def open_position(
    symbol: str,
    direction: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    quantity: int = 10,
    signal_score: float = None,
    confidence: float = None,
    velez_score: Dict = None
) -> Position:
    """Open a new position in shadow portfolio"""
    with get_db_session() as session:
        portfolio = session.query(ShadowPortfolio).first()
        
        position = Position(
            portfolio_id=portfolio.id,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            signal_score=signal_score,
            confidence=confidence,
            velez_score=velez_score,
            is_active=True
        )
        
        session.add(position)
        session.commit()
        
        # Log event
        log_system_event(
            session,
            "POSITION_OPENED",
            f"Opened {direction} position: {symbol} @ ${entry_price}",
            event_metadata={
                "symbol": symbol,
                "entry_price": entry_price,
                "quantity": quantity,
                "confidence": confidence
            }
        )
        
        logger.info(f"✅ Position opened: {symbol} {direction} @ ${entry_price}")
        
        return position


def close_position(position_id: str, exit_price: float, exit_reason: str = "Manual close") -> Trade:
    """Close an active position and record trade"""
    with get_db_session() as session:
        position = session.query(Position).filter(Position.id == position_id).first()
        
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if not position.is_active:
            raise ValueError(f"Position {position_id} is already closed")
        
        # Calculate P&L
        if position.direction == "LONG":
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        pnl_pct = (pnl / (position.entry_price * position.quantity)) * 100
        
        # Calculate duration
        duration = datetime.utcnow() - position.entry_time
        duration_hours = duration.total_seconds() / 3600
        
        # Create trade record
        trade = Trade(
            portfolio_id=position.portfolio_id,
            symbol=position.symbol,
            direction=position.direction,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            stop_price=position.stop_price,
            target_price=position.target_price,
            realized_pnl=pnl,
            realized_pnl_pct=pnl_pct,
            entry_reason=f"Signal score: {position.signal_score}",
            exit_reason=exit_reason,
            signal_score=position.signal_score,
            confidence=position.confidence,
            velez_score=position.velez_score,
            entry_time=position.entry_time,
            exit_time=datetime.utcnow(),
            duration_hours=duration_hours,
            is_winner=pnl > 0
        )
        
        session.add(trade)
        
        # Update portfolio
        portfolio = session.query(ShadowPortfolio).filter(
            ShadowPortfolio.id == position.portfolio_id
        ).first()
        
        portfolio.current_balance += pnl
        portfolio.total_pnl += pnl
        portfolio.total_pnl_pct = ((portfolio.current_balance - portfolio.starting_balance) / portfolio.starting_balance) * 100
        portfolio.total_trades += 1
        
        if trade.is_winner:
            portfolio.winning_trades += 1
        else:
            portfolio.losing_trades += 1
        
        portfolio.win_rate = (portfolio.winning_trades / portfolio.total_trades) * 100 if portfolio.total_trades > 0 else 0
        portfolio.updated_at = datetime.utcnow()
        
        # Mark position as closed
        position.is_active = False
        
        session.commit()
        
        # Log event
        log_system_event(
            session,
            "POSITION_CLOSED",
            f"Closed {position.symbol}: P&L ${pnl:.2f} ({pnl_pct:.2f}%)",
            event_metadata={
                "symbol": position.symbol,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "exit_reason": exit_reason
            }
        )
        
        logger.info(f"✅ Position closed: {position.symbol} | P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        
        return trade


def update_position_prices(symbol: str, current_price: float):
    """Update current price and P&L for all active positions of a symbol"""
    with get_db_session() as session:
        positions = session.query(Position).filter(
            Position.symbol == symbol,
            Position.is_active == True
        ).all()
        
        for position in positions:
            position.current_price = current_price
            
            # Calculate unrealized P&L
            if position.direction == "LONG":
                pnl = (current_price - position.entry_price) * position.quantity
            else:
                pnl = (position.entry_price - current_price) * position.quantity
            
            position.unrealized_pnl = pnl
            position.unrealized_pnl_pct = (pnl / (position.entry_price * position.quantity)) * 100
            position.updated_at = datetime.utcnow()
        
        session.commit()


# ============================================================================
# SIGNAL SERVICES
# ============================================================================

def save_signal(signal_data: Dict) -> SignalHistory:
    """Save generated signal to history"""
    with get_db_session() as session:
        signal = SignalHistory(
            symbol=signal_data['symbol'],
            direction=signal_data['direction'],
            score=signal_data['score'],
            velez_score=signal_data.get('velez_score'),
            explosive_signal=signal_data.get('explosive_signal', False),
            compression_days=signal_data.get('compression_days', 0),
            entry_price=signal_data['entry_price'],
            stop_price=signal_data['stop_price'],
            target_price=signal_data['target_price'],
            whale_data=signal_data.get('whale_data'),
            fresh_ignition=signal_data.get('fresh_ignition'),
            generated_at=datetime.utcnow()
        )
        
        session.add(signal)
        session.commit()
        
        logger.info(f"💾 Signal saved: {signal.symbol} | Score: {signal.score}")
        
        return signal


def get_recent_signals(limit: int = 50) -> List[Dict]:
    """Get recent signal history"""
    with get_db_session() as session:
        signals = session.query(SignalHistory).order_by(
            SignalHistory.generated_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": s.id,
                "symbol": s.symbol,
                "direction": s.direction,
                "score": s.score,
                "explosive_signal": s.explosive_signal,
                "generated_at": s.generated_at.isoformat()
            }
            for s in signals
        ]


# ============================================================================
# SYSTEM EVENT SERVICES
# ============================================================================

def log_system_event(session: Session, event_type: str, message: str, severity: str = "INFO", event_metadata: Dict = None):
    """Log a system event"""
    event = SystemEvent(
        event_type=event_type,
        severity=severity,
        message=message,
        event_metadata=event_metadata,
        timestamp=datetime.utcnow()
    )
    session.add(event)


def get_recent_events(event_type: str = None, limit: int = 50) -> List[Dict]:
    """Get recent system events"""
    with get_db_session() as session:
        query = session.query(SystemEvent)
        
        if event_type:
            query = query.filter(SystemEvent.event_type == event_type)
        
        events = query.order_by(SystemEvent.timestamp.desc()).limit(limit).all()
        
        return [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "message": e.message,
                "event_metadata": e.event_metadata,
                "timestamp": e.timestamp.isoformat()
            }
            for e in events
        ]


# ============================================================================
# MACRO & HEDGE SERVICES
# ============================================================================

def update_macro_regime(regime: str, threat_level: int, factors: Dict = None):
    """Update current macro regime"""
    with get_db_session() as session:
        macro = MacroRegime(
            regime=regime,
            threat_level=threat_level,
            vix=factors.get('vix') if factors else None,
            put_call_ratio=factors.get('put_call_ratio') if factors else None,
            breadth=factors.get('breadth') if factors else None,
            sector_rotation=factors.get('sector_rotation') if factors else None,
            factors=factors,
            timestamp=datetime.utcnow()
        )
        
        session.add(macro)
        session.commit()
        
        logger.info(f"🌍 Macro regime updated: {regime} (Threat: {threat_level}/10)")


def get_current_macro() -> Optional[Dict]:
    """Get current macro regime"""
    with get_db_session() as session:
        macro = session.query(MacroRegime).order_by(
            MacroRegime.timestamp.desc()
        ).first()
        
        if not macro:
            return None
        
        return {
            "regime": macro.regime,
            "threat_level": macro.threat_level,
            "vix": macro.vix,
            "put_call_ratio": macro.put_call_ratio,
            "breadth": macro.breadth,
            "sector_rotation": macro.sector_rotation,
            "timestamp": macro.timestamp.isoformat()
        }


def activate_hedge(symbol: str, contracts: int, entry_price: float, coverage_pct: float, reason: str):
    """Activate a hedge position"""
    with get_db_session() as session:
        hedge = HedgePosition(
            symbol=symbol,
            contracts=contracts,
            entry_price=entry_price,
            current_price=entry_price,
            coverage_pct=coverage_pct,
            activated_reason=reason,
            is_active=True
        )
        
        session.add(hedge)
        session.commit()
        
        log_system_event(
            session,
            "HEDGE_ACTIVATED",
            f"Hedge activated: {symbol} ({contracts} contracts)",
            severity="WARNING",
            event_metadata={"symbol": symbol, "contracts": contracts, "reason": reason}
        )
        
        logger.warning(f"🛡️ HEDGE ACTIVATED: {symbol} | {contracts} contracts | Reason: {reason}")

