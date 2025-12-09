"""
Database Models - Elite Trading System
=======================================

SQLAlchemy models for shadow portfolio, trades, and system state
Tracks all paper trading activity for Aurora dashboard

Author: Elite Trading Team
Date: December 6, 2025
Version: 6.0 (Aurora)
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

# ============================================================================
# SYMBOL UNIVERSE MODEL
# ============================================================================

class SymbolUniverse(Base):
    """Master list of all tradeable symbols"""
    __tablename__ = 'symbol_universe'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(10), nullable=False, unique=True, index=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional enrichment
    sector = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    
    def __repr__(self):
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"<SymbolUniverse {self.symbol} | {status}>"


# ============================================================================
# SHADOW PORTFOLIO MODELS
# ============================================================================

class ShadowPortfolio(Base):
    """Shadow portfolio - tracks paper trading account"""
    __tablename__ = 'shadow_portfolio'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, default="Aurora Shadow Portfolio")
    starting_balance = Column(Float, nullable=False, default=50000.0)
    current_balance = Column(Float, nullable=False)
    total_pnl = Column(Float, default=0.0)
    total_pnl_pct = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ShadowPortfolio {self.name} | Balance: ${self.current_balance:.2f} | P&L: ${self.total_pnl:.2f}>"


class Position(Base):
    """Active position in shadow portfolio"""
    __tablename__ = 'positions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String(36), ForeignKey('shadow_portfolio.id'), nullable=False)
    
    # Position details
    symbol = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # LONG or SHORT
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    
    # P&L tracking
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_pct = Column(Float, default=0.0)
    
    # Signal metadata
    signal_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    velez_score = Column(JSON, nullable=True)  # {"m5": 0.85, "m15": 0.78, "h1": 0.82}
    
    # Timestamps
    entry_time = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    portfolio = relationship("ShadowPortfolio", back_populates="positions")
    
    def __repr__(self):
        return f"<Position {self.symbol} | {self.direction} {self.quantity} @ ${self.entry_price} | P&L: ${self.unrealized_pnl:.2f}>"


class Trade(Base):
    """Completed trade history"""
    __tablename__ = 'trades'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String(36), ForeignKey('shadow_portfolio.id'), nullable=False)
    
    # Trade details
    symbol = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    
    # P&L
    realized_pnl = Column(Float, nullable=False)
    realized_pnl_pct = Column(Float, nullable=False)
    
    # Metadata
    entry_reason = Column(Text, nullable=True)  # Why entered
    exit_reason = Column(Text, nullable=True)  # Why exited
    signal_score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    velez_score = Column(JSON, nullable=True)
    
    # Timestamps
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, default=datetime.utcnow)
    duration_hours = Column(Float, nullable=True)
    
    # Win/Loss
    is_winner = Column(Boolean, nullable=False)
    
    # Relationships
    portfolio = relationship("ShadowPortfolio", back_populates="trades")
    
    def __repr__(self):
        status = "WIN" if self.is_winner else "LOSS"
        return f"<Trade {self.symbol} | {status} | P&L: ${self.realized_pnl:.2f}>"


# ============================================================================
# SIGNAL TRACKING MODELS
# ============================================================================

class SignalHistory(Base):
    """Historical record of all generated signals"""
    __tablename__ = 'signal_history'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Signal details
    symbol = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)
    score = Column(Float, nullable=False)
    
    # Velez analysis
    velez_score = Column(JSON, nullable=True)
    explosive_signal = Column(Boolean, default=False)
    compression_days = Column(Integer, nullable=True)
    
    # Price levels
    entry_price = Column(Float, nullable=False)
    stop_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    
    # Enrichment data
    whale_data = Column(JSON, nullable=True)
    fresh_ignition = Column(JSON, nullable=True)
    
    # Timestamps
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Outcome tracking
    was_traded = Column(Boolean, default=False)
    trade_id = Column(String(36), nullable=True)  # Link to Trade if executed
    
    def __repr__(self):
        return f"<SignalHistory {self.symbol} | Score: {self.score} | {self.generated_at}>"


# ============================================================================
# SYSTEM STATE MODELS
# ============================================================================

class SystemEvent(Base):
    """System events and actions log"""
    __tablename__ = 'system_events'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(50), nullable=False, index=True)  # SCAN, TRADE_ENTRY, TRADE_EXIT, HEDGE_ACTIVATE, etc.
    severity = Column(String(20), default="INFO")  # INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)
    event_metadata = Column(JSON, nullable=True)  # FIXED: renamed from 'metadata'
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<SystemEvent {self.event_type} | {self.severity} | {self.timestamp}>"


class MacroRegime(Base):
    """Macro market regime tracking"""
    __tablename__ = 'macro_regimes'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    regime = Column(String(20), nullable=False)  # PROFIT, CAUTION, DANGER, BUNKER
    threat_level = Column(Integer, nullable=False)  # 1-10
    
    # Indicators
    vix = Column(Float, nullable=True)
    put_call_ratio = Column(Float, nullable=True)
    breadth = Column(String(20), nullable=True)
    sector_rotation = Column(String(50), nullable=True)
    
    # Metadata
    factors = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<MacroRegime {self.regime} | Threat: {self.threat_level}/10 | {self.timestamp}>"


class HedgePosition(Base):
    """Futures hedge positions"""
    __tablename__ = 'hedge_positions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Position details
    symbol = Column(String(10), nullable=False)  # ES_F, NQ_F, etc.
    contracts = Column(Integer, nullable=False)  # Negative for short
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    
    # Coverage
    coverage_pct = Column(Float, nullable=False)  # % of portfolio hedged
    
    # Reason
    activated_reason = Column(Text, nullable=True)
    
    # Timestamps
    activated_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # P&L (when closed)
    pnl = Column(Float, nullable=True)
    
    def __repr__(self):
        status = "ACTIVE" if self.is_active else "CLOSED"
        return f"<HedgePosition {self.symbol} | {self.contracts} contracts | {status}>"


# ============================================================================
# PREDICTION TRACKING MODELS
# ============================================================================

class Prediction(Base):
    """AI prediction tracking for accuracy measurement"""
    __tablename__ = 'predictions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Prediction details
    symbol = Column(String(10), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)  # 1h, 1d, 1w
    direction = Column(String(10), nullable=False)  # UP, DOWN, NEUTRAL
    confidence = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    
    # Brain attribution
    brain_type = Column(String(20), nullable=False)  # MATH, AI, FUSION
    
    # Actual outcome (filled later)
    actual_direction = Column(String(10), nullable=True)
    actual_price = Column(Float, nullable=True)
    was_correct = Column(Boolean, nullable=True)
    
    # Timestamps
    predicted_at = Column(DateTime, default=datetime.utcnow, index=True)
    target_time = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<Prediction {self.symbol} | {self.timeframe} | {self.direction} ({self.confidence:.0%})>"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_all_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(engine)
    

def get_active_positions(session, portfolio_id: str):
    """Get all active positions for a portfolio"""
    return session.query(Position).filter(
        Position.portfolio_id == portfolio_id,
        Position.is_active == True
    ).all()


def get_trade_history(session, portfolio_id: str, limit: int = 50):
    """Get recent trade history"""
    return session.query(Trade).filter(
        Trade.portfolio_id == portfolio_id
    ).order_by(Trade.exit_time.desc()).limit(limit).all()


def get_recent_signals(session, limit: int = 100):
    """Get recent signal history"""
    return session.query(SignalHistory).order_by(
        SignalHistory.generated_at.desc()
    ).limit(limit).all()


def get_system_events(session, event_type: str = None, limit: int = 100):
    """Get recent system events"""
    query = session.query(SystemEvent)
    
    if event_type:
        query = query.filter(SystemEvent.event_type == event_type)
    
    return query.order_by(SystemEvent.timestamp.desc()).limit(limit).all()


def get_current_macro_regime(session):
    """Get the most recent macro regime"""
    return session.query(MacroRegime).order_by(
        MacroRegime.timestamp.desc()
    ).first()


def get_active_hedges(session):
    """Get all active hedge positions"""
    return session.query(HedgePosition).filter(
        HedgePosition.is_active == True
    ).all()
