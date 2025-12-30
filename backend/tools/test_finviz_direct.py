"""Direct Finviz API test tool (bypasses backend)."""
import asyncio
import httpx
import csv
import io
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_finviz_screener():
    """Test Finviz screener API directly."""
    print("\n" + "="*50)
    print("Testing Finviz Screener API Directly")
    print("="*50)
    
    api_key = os.getenv("FINVIZ_API_KEY")
    base_url = os.getenv("FINVIZ_BASE_URL", "https://elite.finviz.com")
    filters = os.getenv("FINVIZ_SCREENER_FILTERS", "cap_midover,sh_avgvol_o500,sh_price_o10")
    version = os.getenv("FINVIZ_SCREENER_VERSION", "111")
    filter_type = os.getenv("FINVIZ_SCREENER_FILTER_TYPE", "4")
    
    url = f"{base_url}/export.ashx"
    params = {
        "v": version,
        "f": filters,
        "ft": filter_type,
        "auth": api_key
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                csv_content = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                stocks = list(csv_reader)
                
                print(f"Total stocks: {len(stocks)}")
                print(f"\nFirst 3 stocks:")
                for i, stock in enumerate(stocks[:3], 1):
                    print(f"\n{i}. {stock}")
                
                return True
            else:
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return False


async def test_finviz_quote():
    """Test Finviz quote API directly."""
    print("\n" + "="*50)
    print("Testing Finviz Quote API Directly")
    print("="*50)
    
    api_key = os.getenv("FINVIZ_API_KEY")
    base_url = os.getenv("FINVIZ_BASE_URL", "https://elite.finviz.com")
    ticker = "MSFT"
    timeframe = "d"
    
    url = f"{base_url}/quote_export.ashx"
    params = {
        "t": ticker,
        "p": timeframe,
        "auth": api_key
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                csv_content = response.text
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                quotes = list(csv_reader)
                
                print(f"Total quotes: {len(quotes)}")
                print(f"\nFirst 3 quotes:")
                for i, quote in enumerate(quotes[:3], 1):
                    print(f"\n{i}. {quote}")
                
                if len(quotes) > 3:
                    print(f"\nLast 3 quotes:")
                    for i, quote in enumerate(quotes[-3:], len(quotes) - 2):
                        print(f"\n{i}. {quote}")
                
                return True
            else:
                print(f"Error: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error: {str(e)}")
            return False


async def main():
    """Run direct Finviz API tests."""
    print("\n" + "="*50)
    print("Finviz Direct API Test Tool")
    print("="*50)
    
    # Test screener
    await test_finviz_screener()
    
    # Test quote
    await test_finviz_quote()
    
    print("\n" + "="*50)
    print("Tests Complete")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())

