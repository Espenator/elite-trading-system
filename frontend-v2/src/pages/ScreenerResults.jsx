import React, { useState } from 'react';

const ScreenerResults = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStock, setSelectedStock] = useState('AAPL');
  const [assetTypes, setAssetTypes] = useState({ stocks: true, options: false, futures: false, crypto: false });
  const [marketCaps, setMarketCaps] = useState({ smallCap: false, midCap: false, largeCap: false });
  const [exchanges, setExchanges] = useState({ nasdaq: false, nyse: false, amex: false });

  const stocks = [
    { symbol: 'AAPL', company: 'Apple Inc.', price: 172.03, change: 1.56, marketCap: '2.7T', peRatio: 28.50 },
    { symbol: 'MSFT', company: 'Microsoft Corp.', price: 420.50, change: 0.98, marketCap: '3.1T', peRatio: 37.15 },
    { symbol: 'GOOG', company: 'Alphabet Inc.', price: 155.70, change: -0.25, marketCap: '1.9T', peRatio: 26.33 },
    { symbol: 'AMZN', company: 'Amazon.com Inc.', price: 180.12, change: 2.10, marketCap: '1.8T', peRatio: 52.88 },
    { symbol: 'TSLA', company: 'Tesla Inc.', price: 175.99, change: -1.05, marketCap: '560B', peRatio: 47.22 },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold">Screener Results</h1>
        <div className="flex gap-3">
          <input 
            type="text"
            placeholder="Search symbols or companies..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-4 py-2 w-80"
          />
          <button className="bg-gray-800 hover:bg-gray-700 border border-gray-700 px-4 py-2 rounded flex items-center gap-2">
            <span>⤓</span> Export Data
          </button>
          <button className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded flex items-center gap-2">
            <span>★</span> Save Filter
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Panel */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800/50 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Filters</h2>
            
            {/* Asset Type */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold mb-3">Asset Type</h3>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" checked={assetTypes.stocks} onChange={() => setAssetTypes({...assetTypes, stocks: !assetTypes.stocks})} className="mr-2" />
                  <span>Stocks</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={assetTypes.options} onChange={() => setAssetTypes({...assetTypes, options: !assetTypes.options})} className="mr-2" />
                  <span>Options</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={assetTypes.futures} onChange={() => setAssetTypes({...assetTypes, futures: !assetTypes.futures})} className="mr-2" />
                  <span>Futures</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={assetTypes.crypto} onChange={() => setAssetTypes({...assetTypes, crypto: !assetTypes.crypto})} className="mr-2" />
                  <span>Crypto</span>
                </label>
              </div>
            </div>

            {/* Price Range */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold mb-3">Price Range</h3>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-400">$0</span>
                <input type="range" min="0" max="2000" className="flex-1" />
                <span className="text-sm text-gray-400">$2000+</span>
              </div>
            </div>

            {/* Market Cap */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold mb-3">Market Cap</h3>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" checked={marketCaps.smallCap} onChange={() => setMarketCaps({...marketCaps, smallCap: !marketCaps.smallCap})} className="mr-2" />
                  <span>Small Cap</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={marketCaps.midCap} onChange={() => setMarketCaps({...marketCaps, midCap: !marketCaps.midCap})} className="mr-2" />
                  <span>Mid Cap</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={marketCaps.largeCap} onChange={() => setMarketCaps({...marketCaps, largeCap: !marketCaps.largeCap})} className="mr-2" />
                  <span>Large Cap</span>
                </label>
              </div>
            </div>

            {/* Exchange */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold mb-3">Exchange</h3>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input type="checkbox" checked={exchanges.nasdaq} onChange={() => setExchanges({...exchanges, nasdaq: !exchanges.nasdaq})} className="mr-2" />
                  <span>NASDAQ</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={exchanges.nyse} onChange={() => setExchanges({...exchanges, nyse: !exchanges.nyse})} className="mr-2" />
                  <span>NYSE</span>
                </label>
                <label className="flex items-center">
                  <input type="checkbox" checked={exchanges.amex} onChange={() => setExchanges({...exchanges, amex: !exchanges.amex})} className="mr-2" />
                  <span>AMEX</span>
                </label>
              </div>
            </div>

            {/* Saved Filters */}
            <div>
              <h3 className="text-sm font-semibold mb-3">Saved Filters</h3>
              <button className="text-sm text-blue-500 hover:text-blue-400">Load saved filter...</button>
            </div>
          </div>
        </div>

        {/* Results Table */}
        <div className="lg:col-span-2">
          <div className="bg-gray-800/50 rounded-lg p-6">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-2">Symbol</th>
                  <th className="text-left py-3 px-2">Company Name</th>
                  <th className="text-right py-3 px-2">Price</th>
                  <th className="text-right py-3 px-2">Change (%)</th>
                  <th className="text-right py-3 px-2">Market Cap</th>
                  <th className="text-right py-3 px-2">P/E Ratio</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((stock) => (
                  <tr 
                    key={stock.symbol} 
                    onClick={() => setSelectedStock(stock.symbol)}
                    className={`border-b border-gray-700/50 cursor-pointer hover:bg-gray-700/30 ${selectedStock === stock.symbol ? 'bg-gray-700/50' : ''}`}
                  >
                    <td className="py-3 px-2 font-semibold">{stock.symbol}</td>
                    <td className="py-3 px-2 text-gray-400">{stock.company}</td>
                    <td className="py-3 px-2 text-right">${stock.price}</td>
                    <td className={`py-3 px-2 text-right ${stock.change > 0 ? 'text-green-500' : 'text-red-500'}`}>
                      {stock.change > 0 ? '+' : ''}{stock.change}%
                    </td>
                    <td className="py-3 px-2 text-right">{stock.marketCap}</td>
                    <td className="py-3 px-2 text-right">{stock.peRatio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center justify-center gap-2 mt-6">
              <button className="px-3 py-1 text-gray-400 hover:text-white">← Previous</button>
              <button className="px-3 py-1 bg-blue-600 rounded">1</button>
              <button className="px-3 py-1 text-gray-400 hover:text-white">2</button>
              <button className="px-3 py-1 text-gray-400 hover:text-white">Next →</button>
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800/50 rounded-lg p-6 space-y-6">
            <div>
              <h2 className="text-2xl font-bold mb-1">{selectedStock}</h2>
              <p className="text-gray-400">Apple Inc.</p>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-3">Overview Chart</h3>
              <div className="h-32 flex items-center justify-center bg-gray-900/50 rounded">
                <p className="text-sm text-blue-500">↗ Miniature Price Chart (Placeholder)</p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-3">Key Metrics</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Price:</span>
                  <span>$172.03</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Change (%):</span>
                  <span className="text-green-500">+1.56%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Market Cap:</span>
                  <span>2.7T</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">P/E Ratio:</span>
                  <span>28.50</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-3">ML Insights</h3>
              <div className="flex gap-2 mb-2">
                <span className="px-2 py-1 bg-blue-600 text-xs rounded">Bullish Trend</span>
                <span className="px-2 py-1 bg-green-600 text-xs rounded">Strong Buy Signal</span>
              </div>
              <p className="text-xs text-gray-400">AI detects increasing institutional interest and positive news sentiment, driving short-term momentum.</p>
            </div>

            <div>
              <h3 className="text-sm font-semibold mb-3">Recent News</h3>
              <ul className="text-xs text-gray-400 space-y-2">
                <li>• Tech giant announces new chip breakthrough, boosting stock outlook.</li>
                <li>• Analysts upgrade rating for company on strong Q3 earnings.</li>
                <li>• Partnership with leading AI firm expands market reach.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScreenerResults;
