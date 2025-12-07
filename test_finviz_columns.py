import requests
from io import StringIO
import pandas as pd

API_KEY = "4475cd42-70ea-4fa7-9630-0d9cd30d9620"

# Test 1: Get screener results
print("="*70)
print("TEST 1: Screener Results")
print("="*70)
url1 = f"https://elite.finviz.com/export.ashx?v=111&f=sec_technology,sh_price_o5&auth={API_KEY}"
response1 = requests.get(url1, timeout=10)

if response1.status_code == 200:
    df1 = pd.read_csv(StringIO(response1.text))
    print(f"✅ SUCCESS! Retrieved {len(df1)} stocks")
    print(f"Columns: {list(df1.columns)}")
    print(f"Sample tickers: {df1['Ticker'].head(5).tolist()}")
else:
    print(f"❌ ERROR: {response1.status_code}")

# Test 2: Get detailed data for specific tickers
print("\n" + "="*70)
print("TEST 2: Detailed Stock Data (NVDA, AAPL)")
print("="*70)
url2 = f"https://elite.finviz.com/export.ashx?v=152&t=NVDA,AAPL&auth={API_KEY}&c=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20"
response2 = requests.get(url2, timeout=10)

if response2.status_code == 200:
    df2 = pd.read_csv(StringIO(response2.text))
    print(f"✅ SUCCESS! Retrieved {len(df2)} stocks")
    print(f"\nColumns ({len(df2.columns)} total):")
    print(list(df2.columns))
    
    print(f"\nNVDA Data:")
    if not df2.empty:
        for col, val in df2.iloc[0].items():
            print(f"  {col}: {val}")
else:
    print(f"❌ ERROR: {response2.status_code}")

print("\n" + "="*70)
