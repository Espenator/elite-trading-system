"""
System Health Checker
Monitors all system components and reports status
"""
import requests
import asyncio
from datetime import datetime
from typing import Dict

class HealthChecker:
    def __init__(self):
        self.components = {
            'backend_api': False,
            'database': False,
            'websocket': False,
            'signal_generation': False,
            'data_collection': False
        }
    
    async def check_backend_api(self) -> bool:
        """Check if backend API is responsive"""
        try:
            response = requests.get('http://localhost:8000/api/health', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    async def check_database(self) -> bool:
        """Check if database is accessible"""
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            # Try a simple query
            signals = db.get_recent_signals(limit=1)
            return True
        except:
            return False
    
    async def check_websocket(self) -> bool:
        """Check if WebSocket is accepting connections"""
        try:
            import websockets
            async with websockets.connect('ws://localhost:8000/ws', timeout=5) as ws:
                await ws.send('{"type": "ping"}')
                response = await asyncio.wait_for(ws.recv(), timeout=2)
                return True
        except:
            return False
    
    async def check_signal_generation(self) -> bool:
        """Check if signal generation is working"""
        try:
            from signal_generation.velez_engine import VelezEngine
            engine = VelezEngine()
            return True
        except:
            return False
    
    async def check_data_collection(self) -> bool:
        """Check if data collection is working"""
        try:
            from data_collection.yfinance_fetcher import fetch_current_price
            price = fetch_current_price('SPY')
            return price > 0
        except:
            return False
    
    async def run_all_checks(self) -> Dict[str, bool]:
        """Run all health checks"""
        self.components['backend_api'] = await self.check_backend_api()
        self.components['database'] = await self.check_database()
        self.components['websocket'] = await self.check_websocket()
        self.components['signal_generation'] = await self.check_signal_generation()
        self.components['data_collection'] = await self.check_data_collection()
        
        return self.components
    
    def get_system_status(self) -> str:
        """Get overall system status"""
        if all(self.components.values()):
            return 'active'
        elif any(self.components.values()):
            return 'degraded'
        else:
            return 'offline'
    
    def print_health_report(self):
        """Print health check report"""
        print("\n" + "="*50)
        print("?? SYSTEM HEALTH REPORT")
        print("="*50)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-"*50)
        
        for component, status in self.components.items():
            icon = "?" if status else "?"
            color = "green" if status else "red"
            print(f"{icon} {component.replace('_', ' ').title()}: {'HEALTHY' if status else 'UNHEALTHY'}")
        
        print("-"*50)
        overall = self.get_system_status()
        print(f"Overall Status: {overall.upper()}")
        print("="*50 + "\n")

async def main():
    """Run health check"""
    checker = HealthChecker()
    await checker.run_all_checks()
    checker.print_health_report()

if __name__ == "__main__":
    asyncio.run(main())
