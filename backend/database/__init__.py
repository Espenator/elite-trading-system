
"""
Database Initialization - Elite Trading System
===============================================

SQLAlchemy engine and session management
Local database = BRAIN of the system
APIs only update data, all computation is LOCAL

Author: Elite Trading Team
Date: December 6, 2025
Version: 6.0 (Aurora)
"""

from sqlalchemy import create_engine, Table, Column, String, Float, Integer, DateTime, Boolean, MetaData, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import os
from pathlib import Path
from datetime import datetime
import asyncio
import time

from backend.core.logger import get_logger
from backend.database.models import Base, ShadowPortfolio

logger = get_logger(__name__)

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Database path - relative to backend directory
# Go up from backend/database/__init__.py to backend/, then to data/
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "aurora_trading.db"

# SQLite connection string
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Scoped session for thread safety
db_session = scoped_session(SessionLocal)

# ============================================================================
# UNIVERSE FILTERS (Tier 1 Criteria)
# ============================================================================

UNIVERSE_FILTERS = {
    "min_price": 10.0,           # No penny stocks
    "max_price": 500000.0,       # No limit on expensive stocks
    "min_volume": 500000,        # 500K+ avg daily volume
    "min_market_cap": 1000000000,  # $1B+ market cap (excludes micro-caps)
    "exclude_sectors": [],       # No exclusions - we want all sectors including leveraged ETFs
}

# ============================================================================
# SYMBOL UNIVERSE TABLE
# ============================================================================

def create_symbols_table():
    """Create symbols table for universe management"""
    metadata = MetaData()
    
    symbols_table = Table('symbols', metadata,
        Column('symbol', String(10), primary_key=True),
        Column('company_name', String(200)),
        Column('sector', String(100)),
        Column('industry', String(100)),
        Column('market_cap', Float),
        Column('last_price', Float),
        Column('avg_volume', Integer),
        Column('is_active', Boolean, default=True),
        Column('added_at', DateTime, default=datetime.utcnow),
        Column('last_updated', DateTime, default=datetime.utcnow),
        extend_existing=True
    )
    
    metadata.create_all(bind=engine)
    return symbols_table

# ============================================================================
# ONE-TIME UNIVERSE POPULATION
# ============================================================================

def populate_symbols_from_apis():
    """
    ONE-TIME: Download ALL qualifying symbols from Finviz
    Apply Tier 1 filters to get ~600-1000 quality stocks
    Store in local database as master universe
    
    NOTE: Using Finviz data directly (no yfinance validation to avoid rate limits)
    """
    logger.info("=" * 80)
    logger.info("🌍 POPULATING SYMBOL UNIVERSE FROM FINVIZ")
    logger.info("=" * 80)
    logger.info(f"Filters: Price ${UNIVERSE_FILTERS['min_price']}-${UNIVERSE_FILTERS['max_price']:,}")
    logger.info(f"         Volume > {UNIVERSE_FILTERS['min_volume']:,}")
    logger.info(f"         Market Cap > ${UNIVERSE_FILTERS['min_market_cap']:,}")
    
    symbols_table = create_symbols_table()
    session = db_session()
    
    try:
        # TIER 1: Get all symbols from Finviz with filters
        logger.info("\n📊 TIER 1: Fetching from Finviz Elite API...")
        
        try:
            from backend.data_collection.finviz_scraper import get_universe_filtered
            
            # Get symbols with Tier 1 filters applied (async call)
            finviz_symbols = asyncio.run(get_universe_filtered(
                min_price=UNIVERSE_FILTERS['min_price'],
                max_price=UNIVERSE_FILTERS['max_price'],
                min_volume=UNIVERSE_FILTERS['min_volume'],
                min_market_cap=UNIVERSE_FILTERS['min_market_cap']
            ))
            
            logger.info(f"✅ Finviz returned {len(finviz_symbols)} qualifying symbols")
            
        except Exception as e:
            logger.error(f"❌ Finviz failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return
        
        # TIER 2: Store Finviz data directly (skip yfinance to avoid rate limits)
        logger.info("\n📥 TIER 2: Storing symbols in database...")
        
        added_count = 0
        skipped_count = 0
        
        for i, symbol_data in enumerate(finviz_symbols):
            # Extract symbol
            symbol = symbol_data.get('symbol') or symbol_data.get('ticker')
            
            if not symbol:
                continue
            
            # Skip if already in database
            existing = session.execute(
                text(f"SELECT symbol FROM symbols WHERE symbol = '{symbol}'")
            ).first()
            
            if existing:
                skipped_count += 1
                continue
            
            try:
                # Use Finviz data directly (already filtered and validated)
                session.execute(
                    symbols_table.insert().values(
                        symbol=symbol,
                        company_name=symbol_data.get('company', ''),
                        sector=symbol_data.get('sector', ''),
                        industry=symbol_data.get('industry', ''),
                        market_cap=symbol_data.get('market_cap', 0),
                        last_price=symbol_data.get('price', 0),
                        avg_volume=symbol_data.get('volume', 0),
                        is_active=True,
                        added_at=datetime.utcnow(),
                        last_updated=datetime.utcnow()
                    )
                )
                
                added_count += 1
                
                # Progress update every 100 symbols
                if added_count % 100 == 0:
                    logger.info(f"📥 Progress: {added_count} symbols added...")
                    session.commit()
                
            except Exception as e:
                logger.error(f"Error adding {symbol}: {e}")
                continue
        
        session.commit()
        
        logger.info("=" * 80)
        logger.info(f"✅ UNIVERSE POPULATION COMPLETE!")
        logger.info(f"   Added: {added_count} symbols")
        logger.info(f"   Skipped (already in DB): {skipped_count}")
        logger.info(f"   Total Universe: {added_count + skipped_count}")
        logger.info("=" * 80)
        
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Universe population failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        session.close()

# ============================================================================
# CONTINUOUS PRICE UPDATES
# ============================================================================

def update_symbol_prices():
    """
    Update current prices for all active symbols
    Called every 5 minutes during market hours
    Uses yfinance batch download for efficiency
    """
    session = db_session()
    
    try:
        # Get all active symbols
        result = session.execute(text("SELECT symbol FROM symbols WHERE is_active = 1"))
        symbols = [row[0] for row in result]
        
        logger.info(f"🔄 Updating prices for {len(symbols)} symbols...")
        
        import yfinance as yf
        
        # Download in batches of 50 for efficiency
        for i in range(0, len(symbols), 50):
            batch = symbols[i:i+50]
            
            try:
                # Download batch (1 minute data)
                data = yf.download(batch, period="1d", interval="1m", progress=False, group_by='ticker')
                
                # Update each symbol
                for symbol in batch:
                    try:
                        if symbol in data:
                            last_price = float(data[symbol]['Close'].iloc[-1])
                            volume = int(data[symbol]['Volume'].iloc[-1])
                            
                            session.execute(
                                text(f"UPDATE symbols SET last_price = {last_price}, "
                                f"last_updated = '{datetime.utcnow().isoformat()}' "
                                f"WHERE symbol = '{symbol}'")
                            )
                    except:
                        continue
                
                session.commit()
                
            except Exception as e:
                logger.error(f"Batch update failed: {e}")
                continue
        
        logger.info("✅ Price update complete")
        
    except Exception as e:
        logger.error(f"❌ Price update failed: {e}")
    finally:
        session.close()

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_database():
    """Initialize database and create all tables"""
    try:
        logger.info("🗄️  Initializing database...")
        
        # Create all tables (models + symbols)
        Base.metadata.create_all(bind=engine)
        create_symbols_table()
        
        # Check shadow portfolio
        session = db_session()
        try:
            portfolio = session.query(ShadowPortfolio).first()
            
            if not portfolio:
                logger.info("Creating default shadow portfolio...")
                portfolio = ShadowPortfolio(
                    name="Aurora Shadow Portfolio",
                    starting_balance=50000.0,
                    current_balance=50000.0,
                    total_pnl=0.0,
                    total_pnl_pct=0.0
                )
                session.add(portfolio)
                session.commit()
                logger.info(f"✅ Shadow portfolio created: {portfolio.id}")
            else:
                logger.info(f"✅ Shadow portfolio loaded: {portfolio.id}")
            
            # Check symbol universe
            try:
                symbol_count = session.execute(text("SELECT COUNT(*) FROM symbols WHERE is_active = 1")).scalar()
                
                if symbol_count == 0:
                    logger.warning("=" * 80)
                    logger.warning("⚠️  SYMBOL UNIVERSE EMPTY!")
                    logger.warning("   Run: populate_symbols_from_apis() to download universe")
                    logger.warning("=" * 80)
                else:
                    logger.info(f"✅ Active symbol universe: {symbol_count} symbols")
            except:
                logger.warning("⚠️  Symbols table not created yet")
                
        finally:
            session.close()
        
        logger.info(f"✅ Database initialized: {DB_PATH}")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def get_db():
    """Get database session (dependency injection for FastAPI)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db_manager():
    """Legacy function for compatibility"""
    class DBManager:
        def get_session(self):
            return SessionLocal()
        
        def close(self):
            pass
    
    return DBManager()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_active_symbols():
    """Get list of all active symbols in universe"""
    with get_db_session() as session:
        result = session.execute(text("SELECT symbol FROM symbols WHERE is_active = 1 ORDER BY symbol"))
        return [row[0] for row in result]


def get_symbol_info(symbol: str):
    """Get detailed info for a specific symbol"""
    with get_db_session() as session:
        result = session.execute(
            text(f"SELECT * FROM symbols WHERE symbol = '{symbol}'")
        ).first()
        
        if result:
            return {
                "symbol": result[0],
                "company_name": result[1],
                "sector": result[2],
                "industry": result[3],
                "market_cap": result[4],
                "last_price": result[5],
                "avg_volume": result[6],
                "is_active": result[7]
            }
        return None

# ============================================================================
# AUTO-INITIALIZE ON IMPORT
# ============================================================================

# Initialize database when module is imported
init_database()


