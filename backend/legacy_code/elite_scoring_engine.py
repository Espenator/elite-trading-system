"""
ELITE SCORING ENGINE v3.1.3 - FIXED INTERFACE
Multi-factor scoring with correct function signature
"""

import pandas as pd
from elite_mode_config import AUTO_FINVIZ_VALIDATE, FINVIZ_SCORE_BOOST

def calculate_elite_score(ticker, price, volume, change, composite_score, direction='long'):
    """
    Calculate elite score for a stock.
    
    Args:
        ticker (str): Stock ticker
        price (float): Stock price
        volume (int): Trading volume
        change (float): Percent change
        composite_score (float): Pre-calculated composite score
        direction (str): 'long' or 'short'
    
    Returns:
        dict: Score data with elite_score
    """
    try:
        # Validate inputs
        if price <= 0 or volume <= 0:
            return {'elite_score': 0, 'finviz_boost': 0}
        
        # Base score from composite
        base_score = composite_score
        
        # Add momentum bonus
        momentum_bonus = min(abs(change) * 2, 10)
        
        # Add liquidity bonus
        liquidity = price * volume
        liquidity_bonus = min(liquidity / 10_000_000, 5)
        
        # Calculate elite score
        elite_score = base_score + momentum_bonus + liquidity_bonus
        
        # Finviz boost (placeholder - no actual validation in simplified version)
        finviz_boost = FINVIZ_SCORE_BOOST if AUTO_FINVIZ_VALIDATE else 0
        elite_score += finviz_boost
        
        # Cap at 100
        elite_score = min(elite_score, 100)
        
        return {
            'elite_score': round(elite_score, 2),
            'finviz_boost': finviz_boost,
            'base_score': round(base_score, 2),
            'momentum_bonus': round(momentum_bonus, 2),
            'liquidity_bonus': round(liquidity_bonus, 2)
        }
        
    except Exception as e:
        return {'elite_score': 0, 'finviz_boost': 0, 'error': str(e)}

def calculate_composite_score(stock_data, direction='long'):
    """Legacy compatibility function"""
    return calculate_elite_score(
        ticker=stock_data.get('Ticker', 'UNKNOWN'),
        price=stock_data.get('Price', 0),
        volume=stock_data.get('Volume', 0),
        change=stock_data.get('Change', 0),
        composite_score=stock_data.get('composite_score', 0),
        direction=direction
    )




