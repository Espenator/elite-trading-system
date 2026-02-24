import React, { useState, useEffect, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faSearch, faDownload, faSave, faChevronDown, faChevronUp,
  faSpinner
} from '@fortawesome/free-solid-svg-icons';
import tradeService from '../services/trade.service';
import { MiniChart } from '../components/MiniChart';

interface StockData {
  symbol: string;
  company: string;
  price: number;
  change: number;
  marketCap: string;
  peRatio: number;
}

interface FilterState {
  [key: string]: boolean;
}

const ITEMS_PER_PAGE = 10;

/** Map Finviz API row to StockData (handles various key names). */
function mapRowToStockData(row: Record<string, unknown>): StockData {
  const priceStr = (row.Price ?? row.price ?? '0').toString().replace(/[^0-9.-]/g, '');
  const changeStr = (row.Change ?? row.change ?? '0').toString().replace(/[^0-9.-]/g, '');
  const peStr = (row['P/E'] ?? row.PE ?? row.pe ?? '0').toString().replace(/[^0-9.-]/g, '');
  return {
    symbol: (row.Ticker ?? row.ticker ?? '').toString().trim(),
    company: (row.Company ?? row.company ?? '').toString().trim(),
    price: parseFloat(priceStr) || 0,
    change: parseFloat(changeStr) || 0,
    marketCap: (row['Market Cap'] ?? row.MarketCap ?? row.market_cap ?? '-').toString().trim(),
    peRatio: parseFloat(peStr) || 0,
  };
}

export default function ScreenerResults() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [priceRange, setPriceRange] = useState<[number, number]>([0, 2000]);
  const [screenerResults, setScreenerResults] = useState<StockData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [assetTypes, setAssetTypes] = useState<FilterState>({
    stocks: true,
    options: false,
    futures: false,
    crypto: false,
  });
  const [marketCaps, setMarketCaps] = useState<FilterState>({
    small: false,
    mid: false,
    large: true,
  });
  const [exchanges, setExchanges] = useState<FilterState>({
    nasdaq: true,
    nyse: true,
    amex: false,
  });
  const [expandedFilters, setExpandedFilters] = useState<FilterState>({
    assetType: true,
    priceRange: true,
    marketCap: true,
    exchange: true,
  });

  // Fetch stock list from Finviz API
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setIsLoading(true);
    tradeService
      .getStockList()
      .then((rows: Record<string, unknown>[]) => {
        if (cancelled) return;
        const mapped = rows.map(mapRowToStockData).filter((s) => s.symbol);
        setScreenerResults(mapped);
        if (mapped.length > 0 && !selectedSymbol) {
          setSelectedSymbol(mapped[0].symbol);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load screener results');
          setScreenerResults([]);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Filter by search (symbol or company)
  const filteredResults = useMemo(() => {
    if (!searchQuery.trim()) return screenerResults;
    const q = searchQuery.trim().toLowerCase();
    return screenerResults.filter(
      (s) =>
        s.symbol.toLowerCase().includes(q) ||
        s.company.toLowerCase().includes(q)
    );
  }, [screenerResults, searchQuery]);

  const totalPages = Math.max(1, Math.ceil(filteredResults.length / ITEMS_PER_PAGE));
  const paginatedResults = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredResults.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredResults, currentPage]);

  const selectedStock =
    screenerResults.find((s) => s.symbol === selectedSymbol) ?? paginatedResults[0] ?? null;

  // Reset to page 1 when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const toggleFilter = (category: string, key: string) => {
    if (category === 'assetType') {
      setAssetTypes(prev => ({ ...prev, [key]: !prev[key] }));
    } else if (category === 'marketCap') {
      setMarketCaps(prev => ({ ...prev, [key]: !prev[key] }));
    } else if (category === 'exchange') {
      setExchanges(prev => ({ ...prev, [key]: !prev[key] }));
    }
  };

  const toggleFilterSection = (section: string) => {
    setExpandedFilters(prev => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Screener Results</h1>
        {error && (
          <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search symbols or companies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2">
            <FontAwesomeIcon icon={faDownload} />
            Export Data
          </button>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2">
            <FontAwesomeIcon icon={faSave} />
            Save Filter
          </button>
        </div>
      </div>

      {/* Main Content - 3 Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Panel - Filters */}
        <div className="lg:col-span-3">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Filters</h2>
            
            {/* Asset Type */}
            <div className="mb-4">
              <button
                onClick={() => toggleFilterSection('assetType')}
                className="w-full flex items-center justify-between text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Asset Type</span>
                <FontAwesomeIcon 
                  icon={expandedFilters.assetType ? faChevronUp : faChevronDown} 
                  className="text-xs text-gray-400"
                />
              </button>
              {expandedFilters.assetType && (
                <div className="space-y-2 pl-2">
                  {Object.entries(assetTypes).map(([key, value]) => (
                    <label key={key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={value}
                        onChange={() => toggleFilter('assetType', key)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="capitalize">{key}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Price Range */}
            <div className="mb-4">
              <button
                onClick={() => toggleFilterSection('priceRange')}
                className="w-full flex items-center justify-between text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Price Range</span>
                <FontAwesomeIcon 
                  icon={expandedFilters.priceRange ? faChevronUp : faChevronDown} 
                  className="text-xs text-gray-400"
                />
              </button>
              {expandedFilters.priceRange && (
                <div className="pl-2">
                  <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-2">
                    <span>${priceRange[0]}</span>
                    <span>${priceRange[1]}+</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="2000"
                    value={priceRange[1]}
                    onChange={(e) => setPriceRange([priceRange[0], Number(e.target.value)])}
                    className="w-full"
                  />
                </div>
              )}
            </div>

            {/* Market Cap */}
            <div className="mb-4">
              <button
                onClick={() => toggleFilterSection('marketCap')}
                className="w-full flex items-center justify-between text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Market Cap</span>
                <FontAwesomeIcon 
                  icon={expandedFilters.marketCap ? faChevronUp : faChevronDown} 
                  className="text-xs text-gray-400"
                />
              </button>
              {expandedFilters.marketCap && (
                <div className="space-y-2 pl-2">
                  {Object.entries(marketCaps).map(([key, value]) => (
                    <label key={key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={value}
                        onChange={() => toggleFilter('marketCap', key)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="capitalize">{key} Cap</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Exchange */}
            <div className="mb-4">
              <button
                onClick={() => toggleFilterSection('exchange')}
                className="w-full flex items-center justify-between text-sm font-medium text-gray-900 dark:text-white mb-2"
              >
                <span>Exchange</span>
                <FontAwesomeIcon 
                  icon={expandedFilters.exchange ? faChevronUp : faChevronDown} 
                  className="text-xs text-gray-400"
                />
              </button>
              {expandedFilters.exchange && (
                <div className="space-y-2 pl-2">
                  {Object.entries(exchanges).map(([key, value]) => (
                    <label key={key} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={value}
                        onChange={() => toggleFilter('exchange', key)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="uppercase">{key}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>

            {/* Saved Filters */}
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Saved Filters</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">No saved filters</p>
            </div>
          </div>
        </div>

        {/* Middle Panel - Results Table */}
        <div className="lg:col-span-5">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Screener Results</h2>
            </div>
            <div className="overflow-x-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-16 text-gray-500 dark:text-gray-400">
                  <FontAwesomeIcon icon={faSpinner} className="animate-spin text-2xl mr-2" />
                  Loading screener results...
                </div>
              ) : (
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-900/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Company Name</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Price</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Change (%)</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Market Cap</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P/E Ratio</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {paginatedResults.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                          No results. Try adjusting your search or filters.
                        </td>
                      </tr>
                    ) : (
                      paginatedResults.map((stock, index) => (
                        <tr
                          key={`${stock.symbol}-${index}`}
                          onClick={() => setSelectedSymbol(stock.symbol)}
                          className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer ${
                            selectedSymbol === stock.symbol ? 'bg-blue-50 dark:bg-blue-900/20' : ''
                          }`}
                        >
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{stock.symbol}</td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{stock.company}</td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">${stock.price.toFixed(2)}</td>
                          <td className={`px-4 py-3 text-sm font-medium ${
                            stock.change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                          }`}>
                            {stock.change >= 0 ? '+' : ''}{stock.change.toFixed(2)}%
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{stock.marketCap}</td>
                          <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{stock.peRatio > 0 ? stock.peRatio.toFixed(2) : '-'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              )}
            </div>
            {/* Pagination */}
            {!isLoading && filteredResults.length > 0 && (
              <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  &lt; Previous
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  Page {currentPage} of {totalPages} ({filteredResults.length} results)
                </span>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage >= totalPages}
                  className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next &gt;
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Detailed View */}
        <div className="lg:col-span-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            {selectedStock ? (
              <>
                <div className="mb-4">
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedStock.symbol}</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400">{selectedStock.company}</p>
                </div>

                {/* Miniature Price Chart */}
                <div className="mb-6 h-32 bg-dark dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 overflow-hidden">
                  <MiniChart symbol={selectedStock.symbol} className="w-full h-full" />
                </div>

                {/* Key Metrics */}
                <div className="mb-6 space-y-3">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Key Metrics</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Price</div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">${selectedStock.price.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Change (%)</div>
                      <div className={`text-sm font-medium ${
                        selectedStock.change >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                      }`}>
                        {selectedStock.change >= 0 ? '+' : ''}{selectedStock.change.toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Market Cap</div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">{selectedStock.marketCap}</div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">P/E Ratio</div>
                      <div className="text-sm font-medium text-gray-900 dark:text-white">{selectedStock.peRatio > 0 ? selectedStock.peRatio.toFixed(2) : '-'}</div>
                    </div>
                  </div>
                </div>

                {/* ML Insights */}
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">ML Insights</h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full text-xs font-medium">
                      Bullish Trend
                    </span>
                    <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 rounded-full text-xs font-medium">
                      Strong Buy Signal
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                    AI detects increasing institutional interest and positive news sentiment, driving short-term momentum.
                  </p>
                </div>

                {/* Recent News */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Recent News</h3>
                  <ul className="space-y-2">
                    <li className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-2">
                      <span className="text-gray-400 mt-1">•</span>
                      <span>Tech giant announces new chip breakthrough, boosting stock outlook.</span>
                    </li>
                    <li className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-2">
                      <span className="text-gray-400 mt-1">•</span>
                      <span>Analysts upgrade rating for company on strong Q3 earnings.</span>
                    </li>
                    <li className="text-xs text-gray-600 dark:text-gray-400 flex items-start gap-2">
                      <span className="text-gray-400 mt-1">•</span>
                      <span>Partnership with leading AI firm expands market reach.</span>
                    </li>
                  </ul>
                </div>
              </>
            ) : (
              <div className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                Select a stock from the table or wait for data to load.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
