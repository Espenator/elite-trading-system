"""API test tool for testing Finviz endpoints."""
import asyncio
import httpx
import json
from typing import Optional


class APITester:
    """Tool for testing the Elite Trading System API."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    async def test_health(self):
        """Test health check endpoint."""
        print("\n" + "="*50)
        print("Testing Health Check")
        print("="*50)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/health")
                print(f"Status: {response.status_code}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                return response.status_code == 200
            except Exception as e:
                print(f"Error: {str(e)}")
                return False
    
    async def test_stock_list(
        self,
        filters: Optional[str] = None,
        version: Optional[str] = None,
        filter_type: Optional[str] = None,
        columns: Optional[str] = None,
        limit: int = 5
    ):
        """Test stock list endpoint."""
        print("\n" + "="*50)
        print("Testing Stock List Endpoint")
        print("="*50)
        
        params = {}
        if filters:
            params["filters"] = filters
        if version:
            params["version"] = version
        if filter_type:
            params["filter_type"] = filter_type
        if columns:
            params["columns"] = columns
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/stocks/list",
                    params=params
                )
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Total stocks returned: {len(data)}")
                    
                    # Show first few stocks
                    print(f"\nFirst {min(limit, len(data))} stocks:")
                    for i, stock in enumerate(data[:limit], 1):
                        print(f"\n{i}. {json.dumps(stock, indent=2)}")
                    
                    return True
                else:
                    print(f"Error: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                return False
    
    async def test_quote_data(
        self,
        ticker: str = "MSFT",
        timeframe: Optional[str] = None,
        duration: Optional[str] = None,
        limit: int = 5
    ):
        """Test quote data endpoint."""
        print("\n" + "="*50)
        print(f"Testing Quote Data Endpoint (Ticker: {ticker})")
        print("="*50)
        
        params = {}
        if timeframe:
            params["p"] = timeframe
        if duration:
            params["r"] = duration
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/quotes/{ticker}",
                    params=params
                )
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"Total quotes returned: {len(data)}")
                    
                    # Show first few quotes
                    print(f"\nFirst {min(limit, len(data))} quotes:")
                    for i, quote in enumerate(data[:limit], 1):
                        print(f"\n{i}. {json.dumps(quote, indent=2)}")
                    
                    # Show last few quotes
                    if len(data) > limit:
                        print(f"\nLast {min(limit, len(data) - limit)} quotes:")
                        for i, quote in enumerate(data[-limit:], len(data) - limit + 1):
                            print(f"\n{i}. {json.dumps(quote, indent=2)}")
                    
                    return True
                else:
                    print(f"Error: {response.text}")
                    return False
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                return False


async def main():
    """Run all API tests."""
    tester = APITester()
    
    print("\n" + "="*50)
    print("Elite Trading System API Test Tool")
    print("="*50)
    
    # Test health check
    await tester.test_health()
    
    # Test stock list
    await tester.test_stock_list(limit=3)
    
    # Test quote data
    await tester.test_quote_data(ticker="MSFT", limit=3)
    await tester.test_quote_data(ticker="AAPL", timeframe="d", duration="ytd", limit=3)
    
    print("\n" + "="*50)
    print("Tests Complete")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())

