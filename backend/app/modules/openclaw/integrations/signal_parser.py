import re
from datetime import datetime

class SignalParser:
    """
    Parse trade signals from Slack messages.
    Supports multiple formats:
    - Simple: "BUY AAPL 150 CALL 30DTE"
    - Detailed: "AAPL May17 150C @ 2.50 target 4.00 stop 1.50"
    - TradingView webhooks: JSON format with ticker, action, price
    """
    
    def __init__(self):
        self.action_keywords = ['BUY', 'SELL', 'LONG', 'SHORT', 'ENTRY', 'EXIT', 'CLOSE']
        self.direction_map = {
            'BUY': 'buy', 'LONG': 'buy', 'ENTRY': 'buy',
            'SELL': 'sell', 'SHORT': 'sell', 'EXIT': 'sell', 'CLOSE': 'sell'
        }
    
    def parse_message(self, text):
        """
        Parse a Slack message and extract trade signal.
        Returns dict with: symbol, action, quantity, option_type, strike, expiry, target, stop
        """
        text = text.upper().strip()
        
        # Try different parsing strategies
        signal = self._parse_simple_format(text)
        if signal:
            return signal
        
        signal = self._parse_detailed_format(text)
        if signal:
            return signal
        
        return None
    
    def _parse_simple_format(self, text):
        """
        Parse format: "BUY AAPL 150 CALL 30DTE"
        """
        # Check for action keyword
        action = None
        for keyword in self.action_keywords:
            if keyword in text:
                action = self.direction_map[keyword]
                break
        
        if not action:
            return None
        
        # Extract symbol (typically 1-5 chars after action)
        symbol_match = re.search(r'\b([A-Z]{1,5})\b', text)
        if not symbol_match:
            return None
        symbol = symbol_match.group(1)
        
        # Check if it's an option
        is_option = 'CALL' in text or 'PUT' in text or 'C' in text or 'P' in text
        
        signal = {
            'symbol': symbol,
            'action': action,
            'quantity': self._extract_quantity(text),
            'asset_type': 'option' if is_option else 'stock'
        }
        
        if is_option:
            signal['option_type'] = 'call' if ('CALL' in text or text.endswith('C')) else 'put'
            signal['strike'] = self._extract_strike(text)
            signal['expiry'] = self._extract_expiry(text)
        
        # Extract prices
        signal['entry_price'] = self._extract_entry_price(text)
        signal['target'] = self._extract_target(text)
        signal['stop'] = self._extract_stop(text)
        
        return signal
    
    def _parse_detailed_format(self, text):
        """
        Parse format: "AAPL May17 150C @ 2.50 target 4.00 stop 1.50"
        """
        # Extract symbol
        symbol_match = re.search(r'^\s*([A-Z]{1,5})', text)
        if not symbol_match:
            return None
        
        symbol = symbol_match.group(1)
        
        # Check for option notation (e.g., "150C" or "150P")
        option_match = re.search(r'(\d+\.?\d*)([CP])\b', text)
        is_option = option_match is not None
        
        signal = {
            'symbol': symbol,
            'action': 'buy',  # Default
            'quantity': self._extract_quantity(text),
            'asset_type': 'option' if is_option else 'stock'
        }
        
        if is_option:
            signal['strike'] = float(option_match.group(1))
            signal['option_type'] = 'call' if option_match.group(2) == 'C' else 'put'
            signal['expiry'] = self._extract_expiry(text)
        
        signal['entry_price'] = self._extract_entry_price(text)
        signal['target'] = self._extract_target(text)
        signal['stop'] = self._extract_stop(text)
        
        return signal
    
    def _extract_quantity(self, text):
        """Extract quantity (contracts/shares)"""
        # Look for patterns like "10x", "qty 10", "10 contracts"
        qty_match = re.search(r'(\d+)\s*(X|CONTRACTS|SHARES|QTY)?', text)
        return int(qty_match.group(1)) if qty_match else 1
    
    def _extract_strike(self, text):
        """Extract strike price"""
        # Look for number before CALL/PUT or followed by C/P
        strike_match = re.search(r'(\d+\.?\d*)\s*(?:CALL|PUT|C|P)', text)
        return float(strike_match.group(1)) if strike_match else None
    
    def _extract_expiry(self, text):
        """Extract expiration date"""
        # Look for patterns: "30DTE", "May17", "05/17"
        dte_match = re.search(r'(\d+)\s*DTE', text)
        if dte_match:
            # Calculate expiry from DTE
            from datetime import timedelta
            dte = int(dte_match.group(1))
            expiry = datetime.now() + timedelta(days=dte)
            return expiry.strftime('%Y-%m-%d')
        
        # Month/Day format
        date_match = re.search(r'([A-Z]{3})(\d{1,2})', text)
        if date_match:
            # TODO: Parse month abbreviation and day
            return None
        
        return None
    
    def _extract_entry_price(self, text):
        """Extract entry price"""
        # Look for @ symbol or "at" keyword
        price_match = re.search(r'[@AT]\s*(\d+\.?\d*)', text)
        return float(price_match.group(1)) if price_match else None
    
    def _extract_target(self, text):
        """Extract target price"""
        target_match = re.search(r'TARGET\s*(\d+\.?\d*)', text)
        return float(target_match.group(1)) if target_match else None
    
    def _extract_stop(self, text):
        """Extract stop loss"""
        stop_match = re.search(r'STOP\s*(\d+\.?\d*)', text)
        return float(stop_match.group(1)) if stop_match else None
    
    def format_signal_summary(self, signal):
        """Format signal as human-readable summary"""
        if not signal:
            return "No valid signal found"
        
        action_emoji = "🟢" if signal['action'] == 'buy' else "🔴"
        
        if signal['asset_type'] == 'option':
            option_type = signal.get('option_type', '').upper()
            strike = signal.get('strike', 'N/A')
            expiry = signal.get('expiry', 'N/A')
            summary = f"""{action_emoji} **{signal['action'].upper()} {signal['symbol']} {strike} {option_type}**
• Expiry: {expiry}
• Quantity: {signal.get('quantity', 1)} contracts"""
        else:
            summary = f"""{action_emoji} **{signal['action'].upper()} {signal['symbol']}**
• Quantity: {signal.get('quantity', 1)} shares"""
        
        if signal.get('entry_price'):
            summary += f"\n• Entry: ${signal['entry_price']:.2f}"
        if signal.get('target'):
            summary += f"\n• Target: ${signal['target']:.2f}"
        if signal.get('stop'):
            summary += f"\n• Stop: ${signal['stop']:.2f}"
        
        return summary

# Singleton instance
signal_parser = SignalParser()
