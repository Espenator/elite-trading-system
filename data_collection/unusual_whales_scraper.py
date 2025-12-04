"""
Unusual Whales web scraper
Scrapes options flow and dark pool data for top 40 symbols
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor

from core.logger import get_logger

logger = get_logger(__name__)

class UnusualWhalesScraper:
    """
    Scrape Unusual Whales for options flow and dark pool data
    NOTE: This is web scraping, may break if site changes.
    Consider upgrading to API if available.
    """
    
    def __init__(self, headless: bool = True, max_workers: int = 4):
        self.headless = headless
        self.max_workers = max_workers
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
        logger.info(f"Unusual Whales scraper initialized (headless={headless})")
    
    def _create_driver(self) -> webdriver.Chrome:
        """Create a Chrome WebDriver instance"""
        options = Options()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        return driver
    
    def scrape_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Scrape data for a single symbol
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Dictionary with whale data, or None if failed
        """
        # Check cache
        cache_key = symbol
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_duration:
                logger.debug(f"Using cached data for {symbol}")
                return cached_data
        
        driver = None
        try:
            driver = self._create_driver()
            
            # Navigate to symbol page
            url = f"https://unusualwhales.com/stock/{symbol}"
            driver.get(url)
            
            # Wait for page load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            time.sleep(2)  # Additional wait for dynamic content
            
            # Extract data (NOTE: These selectors may break if site changes)
            data = {
                'symbol': symbol,
                'whale_trades_24h': self._extract_whale_count(driver),
                'total_premium': self._extract_total_premium(driver),
                'call_premium': 0,
                'put_premium': 0,
                'sentiment': 'NEUTRAL',
                'dark_pool_blocks_7d': 0,
                'dark_pool_sentiment': 'NEUTRAL',
                'scraped_at': time.time()
            }
            
            # Calculate call/put split
            call_pct = self._extract_call_put_ratio(driver)
            if call_pct is not None:
                data['call_premium'] = data['total_premium'] * call_pct
                data['put_premium'] = data['total_premium'] * (1 - call_pct)
                
                if call_pct > 0.6:
                    data['sentiment'] = 'BULLISH'
                elif call_pct < 0.4:
                    data['sentiment'] = 'BEARISH'
            
            # Navigate to dark pool tab
            try:
                dark_pool_tab = driver.find_element(By.LINK_TEXT, "Dark Pool")
                dark_pool_tab.click()
                time.sleep(1)
                
                data['dark_pool_blocks_7d'] = self._extract_dark_pool_blocks(driver)
                data['dark_pool_sentiment'] = self._analyze_dark_pool_sentiment(driver)
            except:
                pass  # Dark pool data not available
            
            # Cache result
            self.cache[cache_key] = (time.time(), data)
            
            logger.debug(f"✅ Scraped {symbol}: {data['sentiment']}, ${data['total_premium']:,.0f} premium")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape {symbol}: {e}")
            return None
            
        finally:
            if driver:
                driver.quit()
    
    def _extract_whale_count(self, driver) -> int:
        """Extract number of whale trades"""
        try:
            # Example selector - UPDATE THIS based on actual site structure
            element = driver.find_element(By.CLASS_NAME, 'whale-count')
            return int(element.text)
        except:
            return 0
    
    def _extract_total_premium(self, driver) -> float:
        """Extract total options premium"""
        try:
            # Example selector - UPDATE THIS
            element = driver.find_element(By.CLASS_NAME, 'total-premium')
            text = element.text.replace('$', '').replace(',', '').replace('M', '000000').replace('K', '000')
            return float(text)
        except:
            return 0.0
    
    def _extract_call_put_ratio(self, driver) -> Optional[float]:
        """Extract call/put ratio (returns call percentage)"""
        try:
            # Example selector - UPDATE THIS
            calls = driver.find_element(By.CLASS_NAME, 'call-premium')
            puts = driver.find_element(By.CLASS_NAME, 'put-premium')
            
            call_val = float(calls.text.replace('$', '').replace(',', ''))
            put_val = float(puts.text.replace('$', '').replace(',', ''))
            
            total = call_val + put_val
            if total > 0:
                return call_val / total
            
        except:
            pass
        
        return None
    
    def _extract_dark_pool_blocks(self, driver) -> int:
        """Extract number of dark pool blocks"""
        try:
            # Example selector - UPDATE THIS
            element = driver.find_element(By.CLASS_NAME, 'dark-pool-count')
            return int(element.text)
        except:
            return 0
    
    def _analyze_dark_pool_sentiment(self, driver) -> str:
        """Analyze dark pool sentiment"""
        try:
            # Example logic - UPDATE THIS
            # Look for net buying vs selling
            return 'ACCUMULATION'  # or 'DISTRIBUTION' or 'NEUTRAL'
        except:
            return 'NEUTRAL'
    
    def scrape_multiple(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Scrape multiple symbols in parallel
        
        Args:
            symbols: List of stock tickers
        
        Returns:
            Dictionary: {symbol: whale_data}
        """
        logger.info(f"🐋 Scraping Unusual Whales for {len(symbols)} symbols...")
        start_time = time.time()
        
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(self.scrape_symbol, symbol): symbol
                for symbol in symbols
            }
            
            from concurrent.futures import as_completed
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data:
                        results[symbol] = data
                except Exception as e:
                    logger.error(f"Error scraping {symbol}: {e}")
        
        duration = time.time() - start_time
        logger.info(f"✅ Scraped {len(results)}/{len(symbols)} symbols in {duration:.1f}s")
        
        return results

# Global instance
scraper = UnusualWhalesScraper()

# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def enrich_signals(signals: List[Dict]) -> List[Dict]:
    """
    Enrich signals with Unusual Whales data
    
    Args:
        signals: List of signal dictionaries
    
    Returns:
        Signals enriched with whale_data field
    """
    if not signals:
        return signals
    
    symbols = [s['symbol'] for s in signals]
    whale_data = scraper.scrape_multiple(symbols)
    
    # Add whale data to signals
    for signal in signals:
        symbol = signal['symbol']
        if symbol in whale_data:
            signal['whale_data'] = whale_data[symbol]
    
    return signals

# =============================================================================
# MANUAL TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with a few symbols
    test_symbols = ['AAPL', 'NVDA', 'TSLA']
    
    print("\n🐋 Testing Unusual Whales scraper...")
    print("NOTE: This will open browser windows (headless=False for testing)\n")
    
    scraper_test = UnusualWhalesScraper(headless=False, max_workers=1)
    
    for symbol in test_symbols:
        print(f"\nScraping {symbol}...")
        data = scraper_test.scrape_symbol(symbol)
        
        if data:
            print(f"  ✅ Success!")
            print(f"     Sentiment: {data['sentiment']}")
            print(f"     Premium: ${data['total_premium']:,.0f}")
            print(f"     Whale trades: {data['whale_trades_24h']}")
        else:
            print(f"  ❌ Failed")
        
        time.sleep(3)  # Avoid rate limiting
