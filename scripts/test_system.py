"""
System test - Verify all components
"""

import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

async def test_all():
    print("🧪 Testing Elite Trading System")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Imports
    print("\n1. Testing imports...")
    try:
        from core.logger import get_logger
        from core.event_bus import event_bus
        from data_collection.yfinance_fetcher import get_data
        print("   ✅ Core imports OK")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        tests_failed += 1
    
    # Test 2: Data fetching
    print("\n2. Testing data fetching...")
    try:
        data = await get_data(['AAPL'], period='5d', interval='1d')
        if 'AAPL' in data and not data['AAPL'].empty:
            print(f"   ✅ Data fetch OK ({len(data['AAPL'])} bars)")
            tests_passed += 1
        else:
            print("   ❌ No data returned")
            tests_failed += 1
    except Exception as e:
        print(f"   ❌ Data fetch failed: {e}")
        tests_failed += 1
    
    # Test 3: API connection
    print("\n3. Testing API...")
    try:
        import requests
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            print("   ✅ API responding")
            tests_passed += 1
        else:
            print("   ❌ API not responding")
            tests_failed += 1
    except:
        print("   ⚠️  API not running (start with: python run.py)")
        tests_failed += 1
    
    # Test 4: Config
    print("\n4. Testing config...")
    try:
        import yaml
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        print(f"   ✅ Config loaded (style: {config['user_preferences']['trading_style']})")
        tests_passed += 1
    except Exception as e:
        print(f"   ❌ Config error: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all())
