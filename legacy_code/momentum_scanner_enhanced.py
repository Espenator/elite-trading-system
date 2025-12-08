"""
momentum_scanner_enhanced.py - Enhanced Momentum Scanner with UW Integration
UPDATED: November 25, 2025 - EMOJI-FREE VERSION
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
import yfinance as yf

import config_enhanced as config
from enhanced_indicators import (
    calculate_hurst_exponent, fit_gjr_garch, analyze_volume_confirmation,
    validate_breakout_volume, detect_rsi_divergence, analyze_vix_term_structure,
    validate_liquidity, estimate_transaction_costs, is_trade_viable_after_costs,
    calculate_enhanced_score, interpret_hurst
)

try:
    from unusual_whales_scraper import UnusualWhalesWebScraper
    UW_AVAILABLE = True
except ImportError:
    UW_AVAILABLE = False
    logging.warning("UW scraper not available")

logger = logging.getLogger(__name__)

class EnhancedMomentumScanner:
    """Elite momentum scanner with academic enhancements + UW integration"""
    
    def __init__(self, custom_config: Optional[Dict] = None):
        self.config = config
        
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        self.vix_structure = None
        self.vix_cache_time = None
        
        self.uw_scraper = None
        if UW_AVAILABLE and getattr(config, 'USE_UW_SCRAPER', False):
            try:
                self.uw_scraper = UnusualWhalesWebScraper(
                    headless=getattr(config, 'UW_HEADLESS_BROWSER', True),
                    use_saved_session=True
                )
                logger.info("UW scraper initialized")
            except Exception as e:
                logger.warning(f"UW scraper init failed: {e}")
                self.uw_scraper = None
        
        logger.info("EnhancedMomentumScanner initialized")
    
    def download_data(self, symbol: str, period: str = '3mo') -> Optional[pd.DataFrame]:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if data.empty or len(data) < config.FRACTAL_LOOKBACK + 10:
                return None
            
            return data
            
        except Exception as e:
            logger.error(f"Error downloading {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def detect_fractal_swing_high(self, data: pd.DataFrame, window: int = 5) -> Tuple[bool, float]:
        if len(data) < window * 2 + 1:
            return False, 0.0
        
        highs = data['High'].values
        center_idx = len(highs) - window - 1
        
        if center_idx < window:
            return False, 0.0
        
        center_high = highs[center_idx]
        left_highs = highs[center_idx-window:center_idx]
        right_highs = highs[center_idx+1:center_idx+window+1]
        
        is_fractal = (center_high == max(left_highs.max(), right_highs.max(), center_high))
        return is_fractal, center_high
    
    def detect_fractal_swing_low(self, data: pd.DataFrame, window: int = 5) -> Tuple[bool, float]:
        if len(data) < window * 2 + 1:
            return False, 0.0
        
        lows = data['Low'].values
        center_idx = len(lows) - window - 1
        
        if center_idx < window:
            return False, 0.0
        
        center_low = lows[center_idx]
        left_lows = lows[center_idx-window:center_idx]
        right_lows = lows[center_idx+1:center_idx+window+1]
        
        is_fractal = (center_low == min(left_lows.min(), right_lows.min(), center_low))
        return is_fractal, center_low
    
    def detect_staircase_pattern(self, data: pd.DataFrame, window: int = 5) -> Dict[str, any]:
        if len(data) < window:
            return {'bullish': 0, 'bearish': 0, 'has_pattern': False}
        
        closes = data['Close'].iloc[-window:].values
        
        bullish_count = 0
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                bullish_count += 1
            else:
                break
        
        bearish_count = 0
        for i in range(1, len(closes)):
            if closes[i] < closes[i-1]:
                bearish_count += 1
            else:
                break
        
        has_pattern = bullish_count >= 3 or bearish_count >= 3
        
        return {'bullish': bullish_count, 'bearish': bearish_count, 'has_pattern': has_pattern}
    
    def calculate_volatility_clustering(self, data: pd.DataFrame, window: int = 20) -> Dict[str, any]:
        if len(data) < window + 10:
            return {'is_clustered': False, 'ratio': 1.0, 'current_vol': 0.0}
        
        returns = data['Close'].pct_change().dropna()
        
        if config.USE_GJR_GARCH:
            garch_result = fit_gjr_garch(returns, window=window)
            return {
                'is_clustered': garch_result.get('is_clustered', False),
                'ratio': garch_result.get('clustering', 1.0),
                'current_vol': garch_result.get('volatility', 0.0),
                'asymmetry': garch_result.get('asymmetry', 0.0),
                'model': 'GJR-GARCH'
            }
        else:
            recent_vol = returns.iloc[-5:].std()
            historical_vol = returns.iloc[-window:].std()
            ratio = recent_vol / historical_vol if historical_vol > 0 else 1.0
            
            return {
                'is_clustered': ratio > config.VOL_CLUSTERING_THRESHOLD,
                'ratio': ratio,
                'current_vol': recent_vol,
                'model': 'SIMPLE'
            }
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        try:
            logger.info(f"Analyzing {symbol}...")
            
            data = self.download_data(symbol)
            if data is None:
                return None
            
            current_price = float(data['Close'].iloc[-1])
            avg_volume_20d = float(data['Volume'].iloc[-20:].mean())
            
            if config.VALIDATE_LIQUIDITY:
                liquidity = validate_liquidity(
                    symbol=symbol, current_price=current_price, avg_volume=avg_volume_20d,
                    min_price=config.MIN_PRICE, min_dollar_volume=config.MIN_AVG_DOLLAR_VOLUME,
                    max_spread_pct=config.MAX_BID_ASK_SPREAD_PCT
                )
                
                if not liquidity['is_liquid']:
                    return None
            
            rsi_series = self.calculate_rsi(data['Close'])
            current_rsi = float(rsi_series.iloc[-1])
            
            has_swing_high, swing_high = self.detect_fractal_swing_high(data, window=config.FRACTAL_WINDOW)
            has_swing_low, swing_low = self.detect_fractal_swing_low(data, window=config.FRACTAL_WINDOW)
            
            staircase = self.detect_staircase_pattern(data, window=config.STAIRCASE_WINDOW)
            vol_cluster = self.calculate_volatility_clustering(data, window=config.GARCH_WINDOW)
            
            volume_analysis = analyze_volume_confirmation(
                volumes=data['Volume'], prices=data['Close'],
                lookback=config.VOLUME_LOOKBACK, spike_multiplier=config.VOLUME_SPIKE_MULTIPLIER
            )
            
            hurst_value = calculate_hurst_exponent(data['Close'], lags=config.HURST_LOOKBACK)
            hurst_regime = interpret_hurst(hurst_value)
            
            if config.USE_RSI_DIVERGENCE:
                rsi_divergence = detect_rsi_divergence(
                    prices=data['Close'], rsi=rsi_series, lookback=config.DIVERGENCE_LOOKBACK
                )
            else:
                rsi_divergence = {'type': 'NONE', 'strength': 0.0}
            
            fractal_score = 70.0 if (has_swing_high or has_swing_low) else 0.0
            
            staircase_score = 0.0
            if staircase['bullish'] >= 3:
                staircase_score = min(100, staircase['bullish'] * 20)
            elif staircase['bearish'] >= 3:
                staircase_score = min(100, staircase['bearish'] * 20)
            
            vol_score = min(100, vol_cluster['ratio'] * 50) if vol_cluster['is_clustered'] else 0.0
            
            base_score = 0.0
            if current_rsi < 30:
                base_score = 80.0
            elif current_rsi > 70:
                base_score = 80.0
            elif 40 <= current_rsi <= 60:
                base_score = 30.0
            
            weights = {
                'fractal': config.WEIGHT_FRACTAL, 'staircase': config.WEIGHT_STAIRCASE,
                'volatility': config.WEIGHT_VOLATILITY, 'base': config.WEIGHT_BASE,
                'volume': config.WEIGHT_VOLUME, 'hurst': config.WEIGHT_HURST,
                'divergence': config.WEIGHT_DIVERGENCE
            }
            
            score_breakdown = calculate_enhanced_score(
                fractal_score=fractal_score, staircase_score=staircase_score,
                volatility_score=vol_score, base_score=base_score,
                volume_analysis=volume_analysis, hurst_value=hurst_value,
                rsi_divergence=rsi_divergence, weights=weights
            )
            
            composite_score = score_breakdown['composite']
            
            setup_type = self.identify_setup_type(
                current_price=current_price, swing_high=swing_high, swing_low=swing_low,
                current_rsi=current_rsi, staircase=staircase, vol_cluster=vol_cluster,
                hurst_regime=hurst_regime, rsi_divergence=rsi_divergence,
                volume_analysis=volume_analysis
            )
            
            if config.REQUIRE_VOLUME_CONFIRMATION and setup_type:
                if not volume_analysis['has_spike']:
                    return None
            
            if config.VALIDATE_HURST:
                if hurst_regime == 'RANDOM_WALK':
                    return None
                
                if setup_type in config.LONG_SETUPS:
                    if 'BREAKOUT' in setup_type and hurst_regime != 'TRENDING':
                        return None
                    if 'REVERSION' in setup_type and hurst_regime != 'MEAN_REVERTING':
                        return None
            
            if config.VALIDATE_COSTS and config.MODEL_TRANSACTION_COSTS:
                costs = estimate_transaction_costs(
                    entry_price=current_price, spread_pct=config.ESTIMATED_SPREAD_PCT,
                    slippage_pct=config.ESTIMATED_SLIPPAGE_PCT, commission=config.COMMISSION_PER_TRADE
                )
                
                expected_return = 3.5
                if not is_trade_viable_after_costs(expected_return, costs['round_trip_cost_pct'], 
                                                   config.MIN_EXPECTED_RETURN_PCT):
                    return None
            uw_flow_data = None
            uw_darkpool_data = None
            
            if self.uw_scraper:
                try:
                    uw_flow_data = self.uw_scraper.get_ticker_flow(symbol)
                    
                    if uw_flow_data['has_flow']:
                        flow_dir = uw_flow_data['direction']
                        flow_prem = uw_flow_data['total_premium']
                        logger.info(f"{symbol}: UW Flow {flow_dir} (${flow_prem:,.0f})")
                        
                        if flow_dir == 'BULLISH' and setup_type in config.LONG_SETUPS:
                            uw_boost = uw_flow_data['score_boost'] * config.WEIGHT_OPTIONS_FLOW
                            composite_score += uw_boost
                            logger.info(f"{symbol}: LONG boosted +{uw_boost:.1f} (UW flow)")
                        
                        elif flow_dir == 'BEARISH' and setup_type in config.SHORT_SETUPS:
                            uw_boost = uw_flow_data['score_boost'] * config.WEIGHT_OPTIONS_FLOW
                            composite_score += uw_boost
                            logger.info(f"{symbol}: SHORT boosted +{uw_boost:.1f} (UW flow)")
                    
                    uw_darkpool_data = self.uw_scraper.get_darkpool_activity(symbol)
                    
                    if uw_darkpool_data['has_darkpool']:
                        darkpool_boost = uw_darkpool_data['score_boost'] * config.WEIGHT_DARKPOOL
                        composite_score += darkpool_boost
                        dp_val = uw_darkpool_data['total_value']
                        logger.info(f"{symbol}: Darkpool +{darkpool_boost:.1f} (${dp_val:,.0f})")
                    
                    if config.FILTER_UPCOMING_EARNINGS:
                        earnings_data = self.uw_scraper.check_upcoming_earnings(symbol)
                        
                        if earnings_data['has_earnings'] and earnings_data['days_until'] < config.EARNINGS_FILTER_DAYS:
                            days = earnings_data['days_until']
                            logger.warning(f"{symbol}: Earnings in {days} days - FILTERED OUT")
                            return None
                    
                except Exception as e:
                    logger.error(f"UW scrape error for {symbol}: {e}")
            
            composite_score = max(0, min(100, composite_score))
            
            if setup_type in config.LONG_SETUPS and composite_score < config.MIN_LONG_SCORE:
                return None
            elif setup_type in config.SHORT_SETUPS and composite_score < config.MIN_SHORT_SCORE:
                return None
            
            return {
                'symbol': symbol,
                'price': current_price,
                'setup_type': setup_type,
                'score': composite_score,
                'score_breakdown': score_breakdown,
                'rsi': current_rsi,
                'swing_high': swing_high,
                'swing_low': swing_low,
                'staircase': staircase,
                'vol_cluster': vol_cluster,
                'volume': volume_analysis,
                'hurst': {'value': hurst_value, 'regime': hurst_regime},
                'rsi_divergence': rsi_divergence,
                'uw_flow': uw_flow_data,
                'uw_darkpool': uw_darkpool_data,
                'liquidity_ok': True,
                'volume_confirmed': volume_analysis['has_spike'],
                'hurst_validated': hurst_regime != 'RANDOM_WALK',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'data_points': len(data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def identify_setup_type(self, current_price, swing_high, swing_low, current_rsi,
                           staircase, vol_cluster, hurst_regime, rsi_divergence, volume_analysis) -> Optional[str]:
        
        if current_rsi < 30 and swing_low > 0:
            if vol_cluster['is_clustered']:
                return 'FRACTAL_OVERSOLD_BOUNCE'
        
        if current_rsi < 25 and volume_analysis['has_spike']:
            return 'ULTRA_SHORT_PANIC_BOUNCE'
        
        if 30 <= current_rsi <= 50 and hurst_regime == 'MEAN_REVERTING':
            return 'ROLLOVER_MEAN_REVERSION'
        
        if staircase['bullish'] >= 3 and volume_analysis['has_spike']:
            return 'FRACTAL_MOMENTUM_BREAKOUT'
        
        if current_rsi > 70 and swing_high > 0:
            if vol_cluster['is_clustered']:
                return 'FRACTAL_OVERBOUGHT_REJECTION'
        
        if current_rsi > 75 and staircase['bearish'] >= 2:
            return 'PARABOLIC_EXHAUSTION'
        
        if rsi_divergence['type'] == 'BEARISH' and volume_analysis['divergence']:
            return 'FAILED_BREAKOUT_SHORT'
        
        if staircase['bearish'] >= 3 and hurst_regime == 'TRENDING':
            return 'SHORT_MOMENTUM'
        
        return None
    
    def scan_universe(self, symbols: List[str]) -> pd.DataFrame:
        logger.info(f"Scanning {len(symbols)} symbols...")
        
        results = []
        for symbol in symbols:
            result = self.analyze_symbol(symbol)
            if result:
                results.append(result)
        
        if not results:
            logger.warning("No signals found")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        long_df = df[df['setup_type'].isin(config.LONG_SETUPS)].sort_values('score', ascending=False).head(config.MAX_LONG_SIGNALS)
        short_df = df[df['setup_type'].isin(config.SHORT_SETUPS)].sort_values('score', ascending=False).head(config.MAX_SHORT_SIGNALS)
        
        result_df = pd.concat([long_df, short_df])
        
        logger.info(f"Found {len(long_df)} LONG and {len(short_df)} SHORT signals")
        
        return result_df
    
    def __del__(self):
        if self.uw_scraper:
            self.uw_scraper.close()




