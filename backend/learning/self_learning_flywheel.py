"""
Self-Learning Flywheel - The closed loop that improves the system
Trade → Log → Learn → Optimize → Trade (better)
"""

from datetime import datetime
from typing import Dict

from backend.core.logger import get_logger
from backend.core.event_bus import event_bus

logger = get_logger(__name__)

class SelfLearningFlywheel:
    """
    Orchestrates the continuous improvement cycle
    """
    
    def __init__(self):
        self.cycle_count = 0
        self.improvements = []
        
        # Subscribe to events
        event_bus.subscribe('trade_closed', self.on_trade_closed)
        event_bus.subscribe('learning_complete', self.on_learning_complete)
        
        logger.info("Self-learning flywheel initialized")
    
    def on_trade_closed(self, event: Dict):
        """Handle trade closure - feed data to learning loop"""
        trade = event['data']
        
        logger.info(f"Flywheel: Trade logged → {trade['symbol']} ({trade['outcome']})")
        
        # Trade data automatically logged by trade_logger
        # Will be used in next Sunday's learning cycle
    
    def on_learning_complete(self, event: Dict):
        """Handle learning completion - record improvement"""
        data = event['data']
        
        self.cycle_count += 1
        
        improvement = {
            'cycle': self.cycle_count,
            'timestamp': datetime.now().isoformat(),
            'win_rate': data['win_rate'],
            'trades_analyzed': data['trades_analyzed']
        }
        
        self.improvements.append(improvement)
        
        logger.info(f"🎯 Flywheel: Cycle {self.cycle_count} complete")
        logger.info(f"   New win rate: {data['win_rate']:.1f}%")
        logger.info(f"   Analyzed: {data['trades_analyzed']} trades")
    
    def get_improvement_trend(self) -> Dict:
        """Get trend of improvements over time"""
        if not self.improvements:
            return {}
        
        first = self.improvements[0]
        latest = self.improvements[-1]
        
        return {
            'cycles_completed': self.cycle_count,
            'initial_win_rate': first['win_rate'],
            'current_win_rate': latest['win_rate'],
            'improvement_pct': latest['win_rate'] - first['win_rate']
        }

# Global instance
flywheel = SelfLearningFlywheel()
