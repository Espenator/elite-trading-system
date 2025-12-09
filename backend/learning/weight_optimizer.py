"""
Weight Optimizer - Grid search for best scoring weights
"""

import itertools
from typing import Dict, List
import numpy as np

from backend.core.logger import get_logger

logger = get_logger(__name__)

def optimize_weights(
    trade_history: List[Dict],
    weight_ranges: Dict[str, tuple]
) -> Dict:
    """
    Find optimal scoring weights via grid search
    
    Args:
        trade_history: Historical trades
        weight_ranges: Dict of {component: (min, max, step)}
    
    Returns:
        Best weights dict
    """
    logger.info("Starting weight optimization...")
    
    # Generate all combinations
    components = list(weight_ranges.keys())
    ranges = [np.arange(vmin, vmax, step) for vmin, vmax, step in weight_ranges.values()]
    
    best_weights = {}
    best_score = 0.0
    tested = 0
    
    for combination in itertools.product(*ranges):
        # Ensure weights sum to 1.0
        weights = {comp: val for comp, val in zip(components, combination)}
        total = sum(weights.values())
        weights = {k: v/total for k, v in weights.items()}
        
        # Evaluate on trade history
        score = evaluate_weights(weights, trade_history)
        
        if score > best_score:
            best_score = score
            best_weights = weights
        
        tested += 1
        
        if tested % 100 == 0:
            logger.info(f"  Tested {tested} combinations...")
    
    logger.info(f"✅ Optimization complete: {tested} combinations tested")
    logger.info(f"   Best score: {best_score:.1%}")
    
    return best_weights

def evaluate_weights(weights: Dict, trade_history: List[Dict]) -> float:
    """
    Evaluate weight combination on historical trades
    
    Returns:
        Score (win rate * avg R-multiple)
    """
    if not trade_history:
        return 0.0
    
    # TODO: Re-score trades with new weights and calculate performance
    # For now, return random score
    return np.random.uniform(0.6, 0.8)
