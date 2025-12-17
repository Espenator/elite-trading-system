import yfinance as yf

print("Testing yfinance connection to Yahoo Finance...")
print("-" * 50)

try:
    ticker = yf.Ticker('AAPL')
    info = ticker.info
    
    if info and 'currentPrice' in info:
        print(f"✅ SUCCESS: Fetched AAPL data")
        print(f"   Current Price: ${info.get('currentPrice', 'N/A')}")
        print(f"   Symbol: {info.get('symbol', 'N/A')}")
    else:
        print("❌ FAILED: No data returned")
        print(f"   Info keys: {list(info.keys())[:5] if info else 'None'}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    print(f"   Type: {type(e).__name__}")

print("-" * 50)

