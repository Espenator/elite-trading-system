"""
Parallel processing orchestrator
Manages all 32 threads on your i9-13900
"""

from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from typing import List, Callable, Any

from core.logger import get_logger

logger = get_logger(__name__)

class ParallelOrchestrator:
    """
    Coordinate parallel tasks across all CPU cores
    """
    
    def __init__(self):
        self.cpu_count = mp.cpu_count()
        logger.info(f"Parallel orchestrator initialized: {self.cpu_count} threads available")
        
        # Thread pools
        self.scan_pool = ThreadPoolExecutor(max_workers=12, thread_name_prefix="scan")
        self.backtest_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="backtest")
        self.scrape_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="scrape")
    
    def run_parallel(self, func: Callable, items: List[Any], pool_type: str = 'scan') -> List:
        """
        Run function on items in parallel
        
        Args:
            func: Function to execute
            items: List of items to process
            pool_type: Which pool to use (scan, backtest, scrape)
        
        Returns:
            List of results
        """
        if pool_type == 'scan':
            pool = self.scan_pool
        elif pool_type == 'backtest':
            pool = self.backtest_pool
        else:
            pool = self.scrape_pool
        
        results = list(pool.map(func, items))
        return results
    
    def shutdown(self):
        """Shutdown all pools"""
        self.scan_pool.shutdown(wait=True)
        self.backtest_pool.shutdown(wait=True)
        self.scrape_pool.shutdown(wait=True)
        logger.info("All thread pools shut down")

# Global instance
orchestrator = ParallelOrchestrator()
