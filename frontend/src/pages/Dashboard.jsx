import { useState, useEffect, useRef, useMemo } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faArrowDown, faCircle, faSort, faSortUp, faSortDown, faSearch, faFilter } from '@fortawesome/free-solid-svg-icons';
import { ChartArea } from '../components/ChartArea';
import tradeService from '../services/trade.service';

export default function Dashboard() {
  const [stocks, setStocks] = useState([]);
  const [positions, setPositions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);
  const intervalRef = useRef(null);

  // Filter and sort state
  const [searchText, setSearchText] = useState('');
  const [filterSector, setFilterSector] = useState('');
  const [filterIndustry, setFilterIndustry] = useState('');
  const [filterCountry, setFilterCountry] = useState('');
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Selected stock for chart
  const [selectedStock, setSelectedStock] = useState(null);

  // Fetch stock data from API
  const fetchStocks = async () => {
    try {
      setIsLoading(true);
      const stockData = await tradeService.getStockList();
      setStocks(stockData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error fetching stocks:', error);
      // Keep previous stocks on error
    } finally {
      setIsLoading(false);
    }
  };

  // Set up polling every 30 seconds
  useEffect(() => {
    // Fetch immediately on mount
    fetchStocks();

    // Set up interval to fetch every 30 seconds
    intervalRef.current = setInterval(() => {
      fetchStocks();
    }, 30000); // 30 seconds

    // Cleanup interval on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Get unique filter values
  const uniqueSectors = useMemo(() => {
    const sectors = [...new Set(stocks.map(s => s.Sector).filter(Boolean))].sort();
    return sectors;
  }, [stocks]);

  const uniqueIndustries = useMemo(() => {
    const industries = [...new Set(stocks.map(s => s.Industry).filter(Boolean))].sort();
    return industries;
  }, [stocks]);

  const uniqueCountries = useMemo(() => {
    const countries = [...new Set(stocks.map(s => s.Country).filter(Boolean))].sort();
    return countries;
  }, [stocks]);

  // Filter and sort stocks
  const filteredAndSortedStocks = useMemo(() => {
    let filtered = [...stocks];

    // Apply text search
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      filtered = filtered.filter(stock => 
        stock.Ticker?.toLowerCase().includes(searchLower) ||
        stock.Company?.toLowerCase().includes(searchLower)
      );
    }

    // Apply filters
    if (filterSector) {
      filtered = filtered.filter(stock => stock.Sector === filterSector);
    }
    if (filterIndustry) {
      filtered = filtered.filter(stock => stock.Industry === filterIndustry);
    }
    if (filterCountry) {
      filtered = filtered.filter(stock => stock.Country === filterCountry);
    }

    // Apply sorting
    if (sortColumn) {
      filtered.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];

        // Handle numeric values
        if (sortColumn === 'Price' || sortColumn === 'Market Cap' || sortColumn === 'P/E' || sortColumn === 'Volume') {
          aVal = parseFloat(aVal?.toString().replace(/[^0-9.-]/g, '') || 0);
          bVal = parseFloat(bVal?.toString().replace(/[^0-9.-]/g, '') || 0);
        }

        // Handle Change percentage
        if (sortColumn === 'Change') {
          aVal = parseFloat(aVal?.toString().replace(/[^0-9.-]/g, '') || 0);
          bVal = parseFloat(bVal?.toString().replace(/[^0-9.-]/g, '') || 0);
        }

        // Handle string comparison
        if (typeof aVal === 'string') {
          aVal = aVal.toLowerCase();
          bVal = bVal?.toLowerCase() || '';
        }

        if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return filtered;
  }, [stocks, searchText, filterSector, filterIndustry, filterCountry, sortColumn, sortDirection]);

  // Paginate stocks
  const paginatedStocks = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    return filteredAndSortedStocks.slice(startIndex, endIndex);
  }, [filteredAndSortedStocks, currentPage, itemsPerPage]);

  // Calculate total pages
  const totalPages = Math.ceil(filteredAndSortedStocks.length / itemsPerPage);

  // Handle sort
  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
    setCurrentPage(1); // Reset to first page on sort
  };

  // Handle filter change
  const handleFilterChange = () => {
    setCurrentPage(1); // Reset to first page on filter
  };

  // Reset filters
  const resetFilters = () => {
    setSearchText('');
    setFilterSector('');
    setFilterIndustry('');
    setFilterCountry('');
    setCurrentPage(1);
  };

  // Mock positions data (can be replaced with API call later)
  useEffect(() => {
    setPositions([
      { symbol: 'MSFT', quantity: 150, avgEntry: 415.50, currentPrice: 420.10, unrealizedPnL: 690.00, pnlToday: 150.00 },
      { symbol: 'GOOG', quantity: 50, avgEntry: 154.00, currentPrice: 155.00, unrealizedPnL: 50.00, pnlToday: -10.00 },
      { symbol: 'AMZN', quantity: 90, avgEntry: 182.00, currentPrice: 180.30, unrealizedPnL: -153.00, pnlToday: -60.00 },
      { symbol: 'TSLA', quantity: 200, avgEntry: 185.00, currentPrice: 189.20, unrealizedPnL: 840.00, pnlToday: -25.00 },
      { symbol: 'NVDA', quantity: 30, avgEntry: 920.00, currentPrice: 915.20, unrealizedPnL: -144.00, pnlToday: -90.00 },
    ]);
  }, []);

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Market Overview</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Real-time market data and trading signals</p>
      </div>

      {/* Market Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">SPY (S&P 500 ETF)</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">$498.75</p>
              <p className="text-sm text-green-500 mt-1 flex items-center">
                <FontAwesomeIcon icon={faArrowUp} className="mr-1" /> +0.85%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">VIX (Volatility Index)</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">17.20</p>
              <p className="text-sm text-red-500 mt-1 flex items-center">
                <FontAwesomeIcon icon={faArrowDown} className="mr-1" /> -1.52%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Market Breadth (Adv/Dec)</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">+1,250</p>
              <p className="text-sm text-green-500 mt-1 flex items-center">
                <FontAwesomeIcon icon={faArrowUp} className="mr-1" /> +8.3%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Sector Performance (Tech)</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">+1.1%</p>
              <p className="text-sm text-green-500 mt-1">Leading</p>
            </div>
          </div>
        </div>
      </div>

      {/* Stock List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Stock List</h2>
            <div className="flex items-center gap-3">
              {isLoading && (
                <span className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
                  <svg className="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Updating...
                </span>
              )}
              {lastUpdate && !isLoading && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Last update: {lastUpdate.toLocaleTimeString()}
                </span>
              )}
              <span className="text-xs text-gray-500 dark:text-gray-400">
                Auto-refresh: 30s
              </span>
            </div>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            {/* Search */}
            <div className="relative">
              <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search ticker/company..."
                value={searchText}
                onChange={(e) => {
                  setSearchText(e.target.value);
                  handleFilterChange();
                }}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Sector Filter */}
            <select
              value={filterSector}
              onChange={(e) => {
                setFilterSector(e.target.value);
                handleFilterChange();
              }}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Sectors</option>
              {uniqueSectors.map(sector => (
                <option key={sector} value={sector}>{sector}</option>
              ))}
            </select>

            {/* Industry Filter */}
            <select
              value={filterIndustry}
              onChange={(e) => {
                setFilterIndustry(e.target.value);
                handleFilterChange();
              }}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Industries</option>
              {uniqueIndustries.map(industry => (
                <option key={industry} value={industry}>{industry}</option>
              ))}
            </select>

            {/* Country Filter */}
            <select
              value={filterCountry}
              onChange={(e) => {
                setFilterCountry(e.target.value);
                handleFilterChange();
              }}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Countries</option>
              {uniqueCountries.map(country => (
                <option key={country} value={country}>{country}</option>
              ))}
            </select>

            {/* Reset Filters Button */}
            {(searchText || filterSector || filterIndustry || filterCountry) && (
              <button
                onClick={resetFilters}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                <FontAwesomeIcon icon={faFilter} className="mr-2" />
                Reset
              </button>
            )}
          </div>

          {/* Results count */}
          <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
            Showing {paginatedStocks.length} of {filteredAndSortedStocks.length} stocks
            {(searchText || filterSector || filterIndustry || filterCountry) && (
              <span> (filtered from {stocks.length} total)</span>
            )}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Ticker')}
                >
                  <div className="flex items-center gap-2">
                    Ticker
                    {sortColumn === 'Ticker' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Company')}
                >
                  <div className="flex items-center gap-2">
                    Company
                    {sortColumn === 'Company' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Sector')}
                >
                  <div className="flex items-center gap-2">
                    Sector
                    {sortColumn === 'Sector' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Industry</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Country</th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Market Cap')}
                >
                  <div className="flex items-center gap-2">
                    Market Cap
                    {sortColumn === 'Market Cap' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('P/E')}
                >
                  <div className="flex items-center gap-2">
                    P/E
                    {sortColumn === 'P/E' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Price')}
                >
                  <div className="flex items-center gap-2">
                    Price
                    {sortColumn === 'Price' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Change')}
                >
                  <div className="flex items-center gap-2">
                    Change
                    {sortColumn === 'Change' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
                  onClick={() => handleSort('Volume')}
                >
                  <div className="flex items-center gap-2">
                    Volume
                    {sortColumn === 'Volume' ? (
                      <FontAwesomeIcon icon={sortDirection === 'asc' ? faSortUp : faSortDown} />
                    ) : (
                      <FontAwesomeIcon icon={faSort} className="text-gray-400" />
                    )}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {paginatedStocks.length === 0 && !isLoading ? (
                <tr>
                  <td colSpan="10" className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    {filteredAndSortedStocks.length === 0 && stocks.length > 0
                      ? 'No stocks match your filters.'
                      : 'No stocks available. Make sure the backend API is running.'}
                  </td>
                </tr>
              ) : (
                paginatedStocks.map((stock, index) => {
                  const change = stock.Change || '0%';
                  const isPositive = !change.includes('-');
                  const changeValue = parseFloat(change.replace(/[^0-9.-]/g, '')) || 0;
                  
                  return (
                    <tr 
                      key={index} 
                      onClick={() => setSelectedStock(stock)}
                      className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors ${
                        selectedStock?.Ticker === stock.Ticker ? 'bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500' : ''
                      }`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {stock.Ticker}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-gray-300">
                        {stock.Company}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {stock.Sector}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                        {stock.Industry}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {stock.Country}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                        ${parseFloat(stock['Market Cap'] || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}M
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                        {stock['P/E'] || '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        ${stock.Price}
                      </td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                        isPositive 
                          ? 'text-green-600 dark:text-green-400' 
                          : 'text-red-600 dark:text-red-400'
                      }`}>
                        <span className="flex items-center">
                          {isPositive ? (
                            <FontAwesomeIcon icon={faArrowUp} className="mr-1" />
                          ) : (
                            <FontAwesomeIcon icon={faArrowDown} className="mr-1" />
                          )}
                          {change}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">
                        {parseInt(stock.Volume?.replace(/[^0-9]/g, '') || 0).toLocaleString()}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
            {/* Items per page selector - left */}
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Items per page:
              </span>
              <select
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>

            {/* Pagination controls - right */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                First
              </button>
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                Previous
              </button>
              
              <span className="px-4 py-1 text-sm text-gray-600 dark:text-gray-400">
                Page {currentPage} of {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                Next
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                Last
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tactical Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Tactical Chart
            {selectedStock && (
              <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                - {selectedStock.Ticker} ({selectedStock.Company})
              </span>
            )}
          </h2>
        </div>
        <div className="p-6" style={{ height: '600px' }}>
          <ChartArea selectedSignal={selectedStock ? { symbol: selectedStock.Ticker } : null} />
        </div>
      </div>

      {/* Active Positions & Risk Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active Positions */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Active Positions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Symbol</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Qty</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Avg Entry</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">Current</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400">P&L</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {positions.map((pos, index) => (
                  <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{pos.symbol}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{pos.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">${pos.avgEntry}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">${pos.currentPrice}</td>
                    <td className={`px-4 py-3 text-sm font-medium ${pos.unrealizedPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {pos.unrealizedPnL >= 0 ? '+' : ''}${pos.unrealizedPnL.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Risk Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Risk Shield Summary</h2>
          </div>
          <div className="p-6 space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Total Exposure</span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">$125,000</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Max Drawdown (YTD)</span>
              <span className="text-lg font-semibold text-red-600">-6.2%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Risk Score</span>
              <span className="text-lg font-semibold text-green-600">Low [3/10]</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600 dark:text-gray-400">Daily Loss Limit</span>
              <span className="text-lg font-semibold text-gray-900 dark:text-white">$5,000 / $10,000</span>
            </div>
          </div>
        </div>
      </div>

      {/* ML Insights */}
      <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg border border-purple-200 dark:border-purple-800 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          <FontAwesomeIcon icon={faCircle} className="text-purple-600 mr-2" />
          ML Insights
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Market Regime</p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">Bullish Trending</p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">Win Rate (Last 30 days)</p>
            <p className="text-xl font-bold text-green-600 mt-1">62.5%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
