"""
Telegram Bot - Real-time alerts to your phone
"""

import os
from dotenv import load_dotenv
from typing import Dict, List
import asyncio

from core.logger import get_logger
from core.event_bus import event_bus

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

class TelegramBot:
    """
    Send trading alerts to Telegram
    """
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            logger.info("✅ Telegram bot initialized")
        else:
            logger.warning("⚠️  Telegram not configured (check .env)")
        
        # Subscribe to events
        event_bus.subscribe('new_signal', self.on_new_signal)
        event_bus.subscribe('position_opened', self.on_position_opened)
        event_bus.subscribe('position_closed', self.on_position_closed)
        event_bus.subscribe('stop_triggered', self.on_stop_triggered)
    
    async def send_message(self, text: str, parse_mode: str = 'Markdown'):
        """
        Send message to Telegram
        
        Args:
            text: Message text (supports Markdown)
            parse_mode: 'Markdown' or 'HTML'
        """
        if not self.enabled:
            return
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.debug("Telegram message sent")
            else:
                logger.error(f"Telegram API error: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
    
    def on_new_signal(self, event: Dict):
        """Handle new signal event"""
        signal = event['data']
        
        # Only alert on high-quality signals (score >= 85)
        if signal['score'] < 85:
            return
        
        text = self._format_signal(signal)
        asyncio.create_task(self.send_message(text))
    
    def on_position_opened(self, event: Dict):
        """Handle position opened event"""
        position = event['data']
        
        text = f"""
🟢 *POSITION OPENED*

Symbol: `{position['symbol']}`
Direction: *{position['direction']}*
Shares: {position['shares']}
Entry: ${position['entry_price']:.2f}
Stop: ${position['stop_loss']:.2f}
Target: ${position['target_1']:.2f}

💰 Cost: ${position['cost_basis']:,.0f}
"""
        asyncio.create_task(self.send_message(text))
    
    def on_position_closed(self, event: Dict):
        """Handle position closed event"""
        trade = event['data']
        
        outcome_emoji = "🟢" if trade['outcome'] == 'WIN' else "🔴"
        
        text = f"""
{outcome_emoji} *POSITION CLOSED*

Symbol: `{trade['symbol']}`
Direction: {trade['direction']}
Entry: ${trade['entry_price']:.2f}
Exit: ${trade['exit_price']:.2f}

💰 P&L: ${trade['pnl']:,.2f}
📊 R-Multiple: {trade['r_multiple']:.2f}R
Reason: {trade['reason']}
"""
        asyncio.create_task(self.send_message(text))
    
    def on_stop_triggered(self, event: Dict):
        """Handle stop loss trigger"""
        order = event['data']
        
        text = f"""
🛑 *STOP LOSS TRIGGERED*

Symbol: `{order['symbol']}`
Stop Price: ${order['stop_price']:.2f}
Fill Price: ${order['fill_price']:.2f}

⚠️ Position closed at loss
"""
        asyncio.create_task(self.send_message(text))
    
    def _format_signal(self, signal: Dict) -> str:
        """Format signal for Telegram"""
        
        explosive_icon = "💥" if signal['explosive_signal'] else ""
        direction_icon = "🟢" if signal['direction'] == 'LONG' else "🔴"
        
        text = f"""
{direction_icon} *NEW SIGNAL* {explosive_icon}

Symbol: `{signal['symbol']}`
Direction: *{signal['direction']}*
Score: *{signal['score']:.1f}*

📊 Velez: {signal['velez_score']['composite']:.1f}
{'💥 Explosive Growth: YES' if signal['explosive_signal'] else ''}
🕐 Fresh: {signal['fresh_ignition']['minutes_since_breakout']}m ago

💵 Entry: ${signal['entry_price']:.2f}
🛑 Stop: ${signal['stop_price']:.2f}
🎯 Target: ${signal['target_price']:.2f}

Risk/Reward: {abs((signal['target_price'] - signal['entry_price']) / (signal['entry_price'] - signal['stop_price'])):.1f}:1
"""
        return text

# Global instance
telegram_bot = TelegramBot()

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def send_alert(message: str):
    """Send custom alert to Telegram"""
    await telegram_bot.send_message(message)

async def send_daily_summary(stats: Dict):
    """Send daily performance summary"""
    text = f"""
📊 *DAILY SUMMARY*

Trades: {stats['total_trades']}
Wins: {stats['wins']} ({stats['win_rate']:.1f}%)
Losses: {stats['losses']}

💰 P&L: ${stats['daily_pnl']:,.2f}
📈 Total Return: {stats['return_pct']:.1f}%

Active Positions: {stats['active_positions']}
"""
    await telegram_bot.send_message(text)

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    async def test():
        if not telegram_bot.enabled:
            print("❌ Telegram not configured")
            print("   Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to .env")
            return
        
        print("📱 Testing Telegram bot...")
        
        # Test message
        await send_alert("🚀 Test message from Elite Trading System!")
        
        print("✅ Check your Telegram!")
    
    asyncio.run(test())
