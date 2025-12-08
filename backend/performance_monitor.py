"""
Performance Monitoring & Metrics
Tracks system performance and latency
"""
import time
import psutil
import asyncio
from datetime import datetime
from typing import Dict, List
from collections import deque

class PerformanceMonitor:
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.api_latencies = deque(maxlen=max_samples)
        self.ws_latencies = deque(maxlen=max_samples)
        self.signal_generation_times = deque(maxlen=max_samples)
        self.start_time = time.time()
        
    def record_api_latency(self, latency_ms: float):
        """Record API request latency"""
        self.api_latencies.append(latency_ms)
    
    def record_ws_latency(self, latency_ms: float):
        """Record WebSocket message latency"""
        self.ws_latencies.append(latency_ms)
    
    def record_signal_generation_time(self, duration_ms: float):
        """Record signal generation time"""
        self.signal_generation_times.append(duration_ms)
    
    def get_metrics(self) -> Dict:
        """Get current performance metrics"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        return {
            'uptime_seconds': int(time.time() - self.start_time),
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_mb': memory.used / 1024 / 1024,
            'api_latency_avg': sum(self.api_latencies) / len(self.api_latencies) if self.api_latencies else 0,
            'api_latency_p95': sorted(self.api_latencies)[int(len(self.api_latencies) * 0.95)] if self.api_latencies else 0,
            'ws_latency_avg': sum(self.ws_latencies) / len(self.ws_latencies) if self.ws_latencies else 0,
            'signal_gen_avg': sum(self.signal_generation_times) / len(self.signal_generation_times) if self.signal_generation_times else 0,
            'timestamp': datetime.now().isoformat()
        }
    
    def print_metrics(self):
        """Print metrics to console"""
        metrics = self.get_metrics()
        print("\n" + "="*50)
        print("?? PERFORMANCE METRICS")
        print("="*50)
        print(f"Uptime: {metrics['uptime_seconds']}s")
        print(f"CPU: {metrics['cpu_percent']:.1f}%")
        print(f"Memory: {metrics['memory_percent']:.1f}% ({metrics['memory_used_mb']:.0f} MB)")
        print(f"API Latency (avg): {metrics['api_latency_avg']:.1f}ms")
        print(f"API Latency (p95): {metrics['api_latency_p95']:.1f}ms")
        print(f"WebSocket Latency: {metrics['ws_latency_avg']:.1f}ms")
        print(f"Signal Gen Time: {metrics['signal_gen_avg']:.1f}ms")
        print("="*50 + "\n")

# Global instance
monitor = PerformanceMonitor()
