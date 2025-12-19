import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faSearch, faDownload, faSave, faChevronDown, faChevronUp,
  faChartLine
} from '@fortawesome/free-solid-svg-icons';

export default function ScreenerResults() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [currentPage, setCurrentPage] = useState(1);
  const [priceRange, setPriceRange] = useState([0, 2000]);
  
  // Filter states
  const [assetTypes, setAssetTypes] = useState({
    stocks: true,
    options: false,
    futures: false,
    crypto: false,
  });
  const [marketCaps, setMarketCaps] = useState({
    small: false,
    mid: false,
    large: true,
  });
  const [exchanges, setExchanges] = useState({
    nasdaq: true,
    nyse: true,
    amex: false,
  });
  const [expandedFilters, setExpandedFilters] = useState({
    assetType: true,
    priceRange: true,
    marketCap: true,
    exchange: true,
  });

  const screenerResults = [
    { symbol: 'AAPL', company: 'Apple Inc.', price: 172.03, change: 1.56, marketCap: '2.7T', peRatio: 28.50 },
    { symbol: 'MSFT', company: 'Microsoft Corp.', price: 420.50, change: 0.98, marketCap: '3.1T', peRatio: 37.15 },
    { symbol: 'GOOG', company: 'Alphabet Inc.', price: 155.70, change: -0.25, marketCap: '1.9T', peRatio: 26.33 },
    { symbol: 'AMZN', company: 'Amazon.com Inc.', price: 180.12, change: 2.10, marketCap: '1.8T', peRatio: 52.88 },
    { symbol: 'TSLA', company: 'Tesla Inc.', price: 175.99, change: -1.05, marketCap: '560B', peRatio: 47.22 },
    { symbol: 'NVDA', company: 'NVIDIA Corp.', price: 915.20, change: 2.45, marketCap: '2.2T', peRatio: 65.30 },
    { symbol: 'META', company: 'Meta Platforms Inc.', price: 485.30, change: 1.20, marketCap: '1.2T', peRatio: 24.15 },
    { symbol: 'JPM', company: 'JPMorgan Chase & Co.', price: 191.20, change: 0.37, marketCap: '550B', peRatio: 12.50 },
  ];

  const selectedStock = screenerResults.find(s => s.symbol === selectedSymbol) || screenerResults[0];

  const toggleFilter = (category, key) => {
    if (category === 'assetType') {
      setAssetTypes(prev => ({ ...prev, [key]: !prev[key] }));
    } else if (category === 'marketCap') {
      setMarketCaps(prev => ({ ...prev, [key]: !prev[key] }));
    } else if (category === 'exchange') {
      setExchanges(prev => ({ ...prev, [key]: !prev[key] }));
    }
  };

  const toggleFilterSection = (section) => {
    setExpandedFilters(prev => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Screener Results</h1>
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
                  {screenerResults.map((stock, index) => (
                    <tr
                      key={index}
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
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{stock.peRatio.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                &lt; Previous
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(1)}
                  className={`px-3 py-1 text-sm rounded ${
                    currentPage === 1
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  1
                </button>
                <button
                  onClick={() => setCurrentPage(2)}
                  className={`px-3 py-1 text-sm rounded ${
                    currentPage === 2
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  2
                </button>
              </div>
              <button
                onClick={() => setCurrentPage(currentPage + 1)}
                disabled={currentPage === 2}
                className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next &gt;
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Detailed View */}
        <div className="lg:col-span-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="mb-4">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">{selectedStock.symbol}</h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">{selectedStock.company}</p>
            </div>

            {/* Miniature Price Chart */}
            <div className="mb-6 h-32 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 flex items-center justify-center">
              <div className="text-center">
                <FontAwesomeIcon icon={faChartLine} className="text-3xl text-gray-400 dark:text-gray-600 mb-2" />
                <p className="text-xs text-gray-500 dark:text-gray-400">Miniature Price Chart</p>
              </div>
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
                  <div className="text-sm font-medium text-gray-900 dark:text-white">{selectedStock.peRatio.toFixed(2)}</div>
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
          </div>
        </div>
      </div>
    </div>
  );
}
