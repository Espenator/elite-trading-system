# app/services/finviz_scraper.py
import httpx
from bs4 import BeautifulSoup
import re
from app.schemas.stock import StockCreate


class FinvizScraper:
    """Scraper for finviz.com stock screener"""
    
    BASE_URL = "https://finviz.com/screener.ashx"
    ELITE_URL = "https://elite.finviz.com/screener.ashx"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
    }

    def __init__(self, use_elite: bool = False):
        self.base_url = self.ELITE_URL if use_elite else self.BASE_URL
        self.client = httpx.Client(headers=self.HEADERS, timeout=30.0, follow_redirects=True)

    def _parse_market_cap(self, value: str) -> str | None:
        """Parse market cap value"""
        if not value or value == "-":
            return None
        return value.strip()

    def _parse_float(self, value: str) -> float | None:
        """Parse float value, handling percentages and dashes"""
        if not value or value == "-":
            return None
        try:
            # Remove % sign and commas
            cleaned = value.replace("%", "").replace(",", "").strip()
            return float(cleaned)
        except (ValueError, AttributeError):
            return None

    def _parse_int(self, value: str) -> int | None:
        """Parse integer value, handling commas"""
        if not value or value == "-":
            return None
        try:
            cleaned = value.replace(",", "").strip()
            return int(cleaned)
        except (ValueError, AttributeError):
            return None

    def _get_total_pages(self, soup: BeautifulSoup) -> int:
        """Get total number of pages from screener"""
        try:
            # Look for the page count text like "1541 / 1549 Total"
            total_text = soup.find(text=re.compile(r"\d+\s*/\s*\d+\s*Total"))
            if total_text:
                match = re.search(r"(\d+)\s*/\s*(\d+)\s*Total", total_text)
                if match:
                    total_stocks = int(match.group(2))
                    # 20 stocks per page in v=111 view
                    return (total_stocks // 20) + (1 if total_stocks % 20 else 0)
            
            # Alternative: look for pagination links
            screener_pages = soup.find_all("a", class_="screener-pages")
            if screener_pages:
                last_page = max([int(a.text) for a in screener_pages if a.text.isdigit()], default=1)
                return last_page
        except Exception:
            pass
        return 1

    def _parse_table_row(self, row) -> StockCreate | None:
        """Parse a single table row into StockCreate"""
        try:
            cells = row.find_all("td")
            if len(cells) < 11:
                return None
            
            # v=111 format: No, Ticker, Company, Sector, Industry, Country, Market Cap, P/E, Price, Change, Volume
            ticker = cells[1].get_text(strip=True)
            if not ticker:
                return None
            
            return StockCreate(
                ticker=ticker,
                company=cells[2].get_text(strip=True),
                sector=cells[3].get_text(strip=True) or None,
                industry=cells[4].get_text(strip=True) or None,
                country=cells[5].get_text(strip=True) or None,
                market_cap=self._parse_market_cap(cells[6].get_text(strip=True)),
                pe_ratio=self._parse_float(cells[7].get_text(strip=True)),
                price=self._parse_float(cells[8].get_text(strip=True)),
                change=self._parse_float(cells[9].get_text(strip=True)),
                volume=self._parse_int(cells[10].get_text(strip=True)),
            )
        except Exception as e:
            print(f"Error parsing row: {e}")
            return None

    def scrape_page(self, filters: str, page: int = 1) -> list[StockCreate]:
        """Scrape a single page of results"""
        stocks = []
        
        # Calculate row offset (r parameter), starts at 1
        row_offset = ((page - 1) * 20) + 1
        
        params = {
            "v": "111",  # Overview view with table
            "f": filters,
            "r": row_offset,
        }
        
        try:
            response = self.client.get(self.base_url, params=params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Find the main table with stock data
            # The table has id="screener-views-table" or class containing "screener"
            table = soup.find("table", {"id": "screener-views-table"})
            if not table:
                # Try alternative selectors
                tables = soup.find_all("table")
                for t in tables:
                    if t.find("td", text=re.compile(r"^[A-Z]{1,5}$")):
                        table = t
                        break
            
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    # Skip header rows
                    if row.find("th"):
                        continue
                    stock = self._parse_table_row(row)
                    if stock:
                        stocks.append(stock)
        
        except httpx.HTTPError as e:
            print(f"HTTP error scraping page {page}: {e}")
        except Exception as e:
            print(f"Error scraping page {page}: {e}")
        
        return stocks

    def scrape_all(self, filters: str, max_pages: int | None = None) -> list[StockCreate]:
        """Scrape all pages of results"""
        all_stocks = []
        
        # Get first page to determine total pages
        params = {"v": "111", "f": filters, "r": 1}
        
        try:
            response = self.client.get(self.base_url, params=params)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            total_pages = self._get_total_pages(soup)
            
            if max_pages:
                total_pages = min(total_pages, max_pages)
            
            print(f"Scraping {total_pages} pages...")
            
            # Parse first page
            table = soup.find("table", {"id": "screener-views-table"})
            if table:
                for row in table.find_all("tr"):
                    if not row.find("th"):
                        stock = self._parse_table_row(row)
                        if stock:
                            all_stocks.append(stock)
            
            # Scrape remaining pages
            for page in range(2, total_pages + 1):
                stocks = self.scrape_page(filters, page)
                all_stocks.extend(stocks)
                print(f"Scraped page {page}/{total_pages}, total stocks: {len(all_stocks)}")
        
        except Exception as e:
            print(f"Error during scrape: {e}")
        
        return all_stocks

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


