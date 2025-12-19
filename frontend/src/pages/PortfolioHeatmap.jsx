import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faDownload, faSync } from '@fortawesome/free-solid-svg-icons';

export default function PortfolioHeatmap() {
  const [dateRange, setDateRange] = useState('Last 30 Days');
  const [aggregation, setAggregation] = useState('Daily');

  const sectors = [
    { name: 'Technology', performance: 3.50, color: 'green' },
    { name: 'Healthcare', performance: -1.20, color: 'red' },
    { name: 'Financials', performance: 0.80, color: 'green' },
    { name: 'Industrials', performance: 2.10, color: 'green' },
    { name: 'Consumer Discretionary', performance: 4.10, color: 'green' },
    { name: 'Communication Services', performance: -0.50, color: 'red' },
    { name: 'Energy', performance: 1.50, color: 'green' },
    { name: 'Utilities', performance: -3.00, color: 'red' },
    { name: 'Real Estate', performance: -2.20, color: 'red' },
    { name: 'Consumer Staples', performance: 0.30, color: 'green' },
    { name: 'Materials', performance: 1.00, color: 'green' },
    { name: 'Information Tech', performance: 5.20, color: 'green' },
  ];

  const positions = [
    { symbol: 'AAPL', company: 'Apple Inc.', quantity: 500, avgPrice: 170.25, currentPrice: 175.80, pnl: 2775.00, pnlPercent: 3.26, sector: 'Technology' },
    { symbol: 'MSFT', company: 'Microsoft Corp.', quantity: 300, avgPrice: 400.10, currentPrice: 402.50, pnl: 720.00, pnlPercent: 0.60, sector: 'Technology' },
    { symbol: 'GOOGL', company: 'Alphabet Inc.', quantity: 150, avgPrice: 155.00, currentPrice: 152.10, pnl: -435.00, pnlPercent: -1.87, sector: 'Communication Services' },
    { symbol: 'JPM', company: 'JPMorgan Chase & Co.', quantity: 200, avgPrice: 190.50, currentPrice: 191.20, pnl: 140.00, pnlPercent: 0.37, sector: 'Financials' },
    { symbol: 'LLY', company: 'Eli Lilly and Company', quantity: 75, avgPrice: 770.00, currentPrice: 765.50, pnl: -337.50, pnlPercent: -0.58, sector: 'Healthcare' },
    { symbol: 'TSLA', company: 'Tesla Inc.', quantity: 100, avgPrice: 185.00, currentPrice: 189.50, pnl: 450.00, pnlPercent: 2.43, sector: 'Consumer Discretionary' },
    { symbol: 'XOM', company: 'Exxon Mobil Corp.', quantity: 250, avgPrice: 110.00, currentPrice: 111.80, pnl: 450.00, pnlPercent: 1.64, sector: 'Energy' },
  ];

  const portfolioSummary = {
    totalValue: 1250000.00,
    dailyPnL: 5200.75,
    dailyPnLPercent: 0.42,
    totalPnL: 125150.20,
    totalPnLPercent: 11.10,
    exposure: 85,
    maxDrawdown: -2.5,
    sharpeRatio: 1.85,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Portfolio Heatmap</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Visualize portfolio performance across sectors and positions</p>
        </div>
        <div className="flex items-center gap-4">
          {/* Date Range */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">Date Range:</label>
            <select
              value={dateRange}
              onChange={(e) => setDateRange(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option>Last 7 Days</option>
              <option>Last 30 Days</option>
              <option>Last 90 Days</option>
              <option>Last Year</option>
              <option>YTD</option>
            </select>
          </div>
          {/* Aggregation */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">Aggregation:</label>
            <select
              value={aggregation}
              onChange={(e) => setAggregation(e.target.value)}
              className="px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option>Hourly</option>
              <option>Daily</option>
              <option>Weekly</option>
              <option>Monthly</option>
            </select>
          </div>
        </div>
      </div>

      {/* Sector Heatmap and Portfolio Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sector Heatmap - Takes 2 columns */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Sector Performance</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {sectors.map((sector, index) => (
                <div
                  key={index}
                  className={`rounded-lg p-4 border-2 transition-all hover:scale-105 cursor-pointer ${
                    sector.color === 'green'
                      ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                  }`}
                >
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {sector.name}
                  </div>
                  <div
                    className={`text-xl font-bold ${
                      sector.color === 'green'
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {sector.performance > 0 ? '+' : ''}
                    {sector.performance.toFixed(2)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Portfolio Summary - Takes 1 column */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Portfolio Summary</h2>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total Portfolio Value</div>
              <div className="text-xl font-bold text-gray-900 dark:text-white">
                ${portfolioSummary.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Daily P&L</div>
              <div className="text-lg font-bold text-green-600 dark:text-green-400">
                +${portfolioSummary.dailyPnL.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-sm text-green-600 dark:text-green-400">
                +{portfolioSummary.dailyPnLPercent.toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total P&L</div>
              <div className="text-lg font-bold text-green-600 dark:text-green-400">
                +${portfolioSummary.totalPnL.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-sm text-green-600 dark:text-green-400">
                +{portfolioSummary.totalPnLPercent.toFixed(2)}%
              </div>
            </div>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Portfolio Exposure</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{portfolioSummary.exposure}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Max Drawdown (30D)</span>
                <span className="text-sm font-semibold text-red-600">{portfolioSummary.maxDrawdown.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Sharpe Ratio (1Y)</span>
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{portfolioSummary.sharpeRatio.toFixed(2)}</span>
              </div>
            </div>
            <div className="pt-4 space-y-2">
              <button className="w-full py-2 px-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
                <FontAwesomeIcon icon={faSync} />
                Rebalance Portfolio
              </button>
              <button className="w-full py-2 px-4 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors flex items-center justify-center gap-2">
                <FontAwesomeIcon icon={faDownload} />
                Export Data
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Positions */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Detailed Positions</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Company Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Quantity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Avg. Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Current Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P&L (%)</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Sector</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {positions.map((position, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{position.symbol}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{position.company}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{position.quantity.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">${position.avgPrice.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">${position.currentPrice.toFixed(2)}</td>
                  <td className={`px-6 py-4 text-sm font-medium ${
                    position.pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {position.pnl >= 0 ? '+' : ''}${position.pnl.toFixed(2)}
                  </td>
                  <td className={`px-6 py-4 text-sm font-medium ${
                    position.pnlPercent >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{position.sector}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Performance Breakdown & Risk Contribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance Breakdown */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Performance Breakdown</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Detailed view of performance by strategy and asset class.
          </p>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-8 text-center border border-gray-200 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Placeholder for performance charts and tables.</p>
          </div>
        </div>

        {/* Risk Contribution */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Risk Contribution</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Analyze each position's contribution to overall portfolio risk.
          </p>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-8 text-center border border-gray-200 dark:border-gray-700">
            <p className="text-gray-500 dark:text-gray-400">Placeholder for risk contribution analysis.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
