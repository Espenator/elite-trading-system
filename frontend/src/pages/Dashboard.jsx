import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faArrowDown, faCircle } from '@fortawesome/free-solid-svg-icons';
import { ChartArea } from '../components/ChartArea';

export default function Dashboard() {
  const [liveSignals, setLiveSignals] = useState([]);
  const [positions, setPositions] = useState([]);

  // Mock data for demonstration
  useEffect(() => {
    setLiveSignals([
      { time: '14:30:15', symbol: 'MSFT', tier: 'T3', score: 92, entry: 420.10, target: 425.50, stop: 418.00, rr: 2.5, action: 'BUY' },
      { time: '14:29:40', symbol: 'AAPL', tier: 'B+', score: 88, entry: 172.55, target: 175.00, stop: 171.80, rr: 3.2, action: 'BUY' },
      { time: '14:28:05', symbol: 'NVDA', tier: 'A-', score: 90, entry: 915.20, target: 905.00, stop: 920.00, rr: 2.0, action: 'SELL' },
      { time: '14:27:10', symbol: 'GOOG', tier: 'C+', score: 75, entry: 155.00, target: 158.50, stop: 154.50, rr: 1.5, action: 'BUY' },
      { time: '14:26:30', symbol: 'AMZN', tier: 'B', score: 85, entry: 180.30, target: 178.00, stop: 181.20, rr: 2.4, action: 'SELL' },
    ]);

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

      {/* Live Trading Signals */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Live Trading Signals</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Tier</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Entry</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Target</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Stop</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">R:R</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {liveSignals.map((signal, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{signal.time}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{signal.symbol}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      signal.tier === 'T3' || signal.tier === 'A-' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300' :
                      signal.tier === 'B+' || signal.tier === 'B' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                      'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                    }`}>
                      {signal.tier}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{signal.score}%</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">${signal.entry}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">${signal.target}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">${signal.stop}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-300">{signal.rr}:1</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-3 py-1 rounded text-xs font-medium ${
                      signal.action === 'BUY' 
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' 
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                    }`}>
                      {signal.action}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tactical Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Tactical Chart</h2>
        </div>
        <div className="p-6" style={{ height: '500px' }}>
          <ChartArea selectedSignal={null} />
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
