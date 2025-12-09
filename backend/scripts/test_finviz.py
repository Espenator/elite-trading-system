import requests
from io import StringIO
import pandas as pd

API_KEY = "4475cd42-70ea-4fa7-9630-0d9cd30d9620"
url = f"https://elite.finviz.com/export.ashx?v=111&f=sec_technology,sh_price_o5&auth={API_KEY}"

print("Testing Finviz Elite API...")
response = requests.get(url, timeout=10)

if response.status_code == 200:
    df = pd.read_csv(StringIO(response.text))
    print(f"✅ SUCCESS! Retrieved {len(df)} stocks")
    print(f"Sample: {df['Ticker'].head(10).tolist()}")
else:
    print(f"❌ ERROR: {response.status_code}")
