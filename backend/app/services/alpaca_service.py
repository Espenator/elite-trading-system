"""Alpaca Markets API service for order execution."""
import httpx
from typing import Dict, Optional
from app.core.config import settings


class AlpacaService:
    """Service for interacting with Alpaca Markets API."""
    
    def __init__(self):
        """Initialize Alpaca service with API credentials."""
        self.base_url = "https://paper-api.alpaca.markets/v2"
        self.api_key = settings.ALPACA_API_KEY
        self.secret_key = settings.ALPACA_SECRET_KEY
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Alpaca API requests."""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "accept": "application/json",
            "content-type": "application/json"
        }
    
    def _map_order_type(self, order_type: str) -> str:
        """Map our order type to Alpaca's order type."""
        mapping = {
            "Market": "market",
            "Limit": "limit",
            "Stop": "stop",
            "Stop Limit": "stop_limit",
            "Trailing Stop": "trailing_stop"
        }
        return mapping.get(order_type, "market")
    
    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        quantity: int,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Dict:
        """
        Create an order through Alpaca API.
        
        Args:
            symbol: Stock symbol
            order_type: Order type (Market, Limit, Stop, Stop Limit)
            side: Order side (buy, sell)
            quantity: Number of shares
            price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: Time in force (day, gtc, ioc, fok)
        
        Returns:
            Alpaca order response
        """
        alpaca_type = self._map_order_type(order_type)
        
        # Build order payload
        order_data = {
            "symbol": symbol.upper(),
            "qty": str(quantity),
            "side": side.lower(),
            "type": alpaca_type,
            "time_in_force": time_in_force
        }
        
        # Add limit_price for limit and stop_limit orders
        if alpaca_type in ["limit", "stop_limit"] and price:
            order_data["limit_price"] = str(price)
        
        # Add stop_price for stop and stop_limit orders
        if alpaca_type in ["stop", "stop_limit"] and stop_price:
            order_data["stop_price"] = str(stop_price)
        elif alpaca_type in ["stop", "stop_limit"] and price:
            # Use price as stop_price if stop_price not provided
            order_data["stop_price"] = str(price)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/orders",
                    headers=self._get_headers(),
                    json=order_data,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 403:
                    error_detail = response.json() if response.content else {}
                    raise Exception(f"Forbidden: {error_detail.get('message', 'Buying power or shares is not sufficient')}")
                elif response.status_code == 422:
                    error_detail = response.json() if response.content else {}
                    raise Exception(f"Unprocessable: {error_detail.get('message', 'Input parameters are not recognized')}")
                else:
                    error_detail = response.json() if response.content else {}
                    raise Exception(f"Alpaca API error: {response.status_code} - {error_detail.get('message', response.text)}")
        except httpx.TimeoutException:
            raise Exception("Request to Alpaca API timed out")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Alpaca API: {str(e)}")
    
    async def get_order(self, order_id: str) -> Dict:
        """Get order details from Alpaca by order ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    error_detail = response.json() if response.content else {}
                    raise Exception(f"Failed to get order: {response.status_code} - {error_detail.get('message', response.text)}")
        except httpx.TimeoutException:
            raise Exception("Request to Alpaca API timed out")
        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to Alpaca API: {str(e)}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order through Alpaca API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/orders/{order_id}",
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                return response.status_code == 204
        except Exception as e:
            raise Exception(f"Failed to cancel order: {str(e)}")


# Global Alpaca service instance
alpaca_service = AlpacaService()

