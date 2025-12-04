"""
Event bus for real-time communication between components
"""

from typing import Dict, List, Callable, Any
from datetime import datetime
from loguru import logger
import threading

class EventBus:
    """
    Pub/sub system for inter-component communication
    
    Example:
        bus = EventBus()
        bus.subscribe('new_signal', on_signal_handler)
        bus.publish('new_signal', {'symbol': 'AAPL', 'score': 92})
    """
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()
        logger.info("EventBus initialized")
    
    def subscribe(self, event_type: str, callback: Callable):
        """
        Subscribe to an event type
        
        Args:
            event_type: Event name (e.g., 'new_signal', 'position_opened')
            callback: Function to call when event is published
        """
        with self.lock:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            
            self.subscribers[event_type].append(callback)
            logger.debug(f"Subscribed to event: {event_type}")
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """Remove a subscription"""
        with self.lock:
            if event_type in self.subscribers:
                self.subscribers[event_type].remove(callback)
                logger.debug(f"Unsubscribed from event: {event_type}")
    
    def publish(self, event_type: str, data: Any = None):
        """
        Publish an event to all subscribers
        
        Args:
            event_type: Event name
            data: Event payload (any JSON-serializable data)
        """
        with self.lock:
            if event_type not in self.subscribers:
                return
            
            callbacks = self.subscribers[event_type].copy()
        
        # Call callbacks outside lock to avoid deadlock
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.debug(f"Publishing event: {event_type}")
        
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
    
    def clear(self, event_type: str = None):
        """Clear all subscribers for an event type (or all)"""
        with self.lock:
            if event_type:
                self.subscribers.pop(event_type, None)
            else:
                self.subscribers.clear()

# Global event bus instance
event_bus = EventBus()
