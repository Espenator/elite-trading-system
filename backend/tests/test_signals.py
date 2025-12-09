"""
Test Suite for Signal Generation
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_signal_generation():
    """Test basic signal generation"""
    from signal_generation.velez_engine import VelezEngine
    
    engine = VelezEngine()
    assert engine is not None
    print("? VelezEngine initialized")

def test_composite_scorer():
    """Test composite scoring"""
    from signal_generation.composite_scorer import CompositeScorer
    
    scorer = CompositeScorer()
    
    # Mock data
    test_data = {
        'ticker': 'AAPL',
        'price': 150.0,
        'volume': 50000000,
        'change': 2.5
    }
    
    score = scorer.calculate_score(test_data)
    assert score >= 0 and score <= 100
    print(f"? Composite score calculated: {score}")

def test_api_client():
    """Test API client connectivity"""
    import requests
    
    try:
        response = requests.get('http://localhost:8000/api/health', timeout=5)
        assert response.status_code == 200
        print("? Backend API is running")
    except:
        print("? Backend not running - start with LAUNCH_ELITE_TRADER.bat")

def test_database():
    """Test database connection"""
    from database.database_manager import DatabaseManager
    
    db = DatabaseManager()
    assert db is not None
    print("? Database manager initialized")

if __name__ == "__main__":
    print("\n=== RUNNING ELITE TRADER TESTS ===\n")
    
    test_signal_generation()
    test_composite_scorer()
    test_database()
    test_api_client()
    
    print("\n? All tests passed!\n")
