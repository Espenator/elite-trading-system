import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faChessKnight, faPlay, faPause, faStop, faEye, faEdit, faPlus,
  faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons';

export default function StrategySettings() {
  // Emergency Controls
  const [masterSwitch, setMasterSwitch] = useState(true);
  const [pauseAllStrategies, setPauseAllStrategies] = useState(false);
  const [closeAllPositions, setCloseAllPositions] = useState(false);

  // Trading Strategies Data
  const strategies = [
    {
      id: 1,
      name: 'Momentum Scalper v2',
      status: 'Active',
      statusColor: 'green',
      description: 'Aggressive short-term momentum strategy with tight stop-losses.',
      dailyPnL: 1.25,
      dailyPnLColor: 'green',
      winRate: 68,
      maxDrawdown: -3.1,
    },
    {
      id: 2,
      name: 'Trend Follower FX',
      status: 'Paused',
      statusColor: 'orange',
      description: 'Medium-term trend following strategy across major FX pairs.',
      dailyPnL: 0.10,
      dailyPnLColor: 'green',
      winRate: 55,
      maxDrawdown: -5.8,
    },
    {
      id: 3,
      name: 'Arbitrage Crypto',
      status: 'Error',
      statusColor: 'red',
      description: 'Cross-exchange cryptocurrency arbitrage with automated execution.',
      dailyPnL: -0.50,
      dailyPnLColor: 'red',
      winRate: 72,
      maxDrawdown: -1.2,
    },
    {
      id: 4,
      name: 'Mean Reversion Stocks',
      status: 'Active',
      statusColor: 'green',
      description: 'Equity mean reversion strategy focused on undervalued stocks.',
      dailyPnL: 0.80,
      dailyPnLColor: 'green',
      winRate: 62,
      maxDrawdown: -2.5,
    },
  ];

  // Strategy Signals Monitor Data
  const strategySignals = [
    { timestamp: '2024-07-26 09:30:15', strategy: 'Momentum Scalper v2', symbol: 'AAPL', direction: 'Buy', confidence: 'High', status: 'Executed' },
    { timestamp: '2024-07-26 09:31:02', strategy: 'Trend Follower FX', symbol: 'EUR/USD', direction: 'Sell', confidence: 'Medium', status: 'Pending' },
    { timestamp: '2024-07-26 09:32:40', strategy: 'Arbitrage Crypto', symbol: 'BTC/USDT', direction: 'Buy', confidence: 'Low', status: 'Rejected' },
    { timestamp: '2024-07-26 09:33:10', strategy: 'Momentum Scalper v2', symbol: 'MSFT', direction: 'Sell', confidence: 'High', status: 'Executed' },
    { timestamp: '2024-07-26 09:34:55', strategy: 'Mean Reversion Stocks', symbol: 'GOOGL', direction: 'Buy', confidence: 'Medium', status: 'Executed' },
  ];

  // Strategy Performance Comparison Data
  const performanceComparison = [
    { strategy: 'Momentum Scalper v2', totalPnL: 25450.00, winRate: 68, sharpeRatio: 1.8, maxDrawdown: -8.5 },
    { strategy: 'Trend Follower FX', totalPnL: 12100.00, winRate: 55, sharpeRatio: 0.9, maxDrawdown: -15.2 },
    { strategy: 'Arbitrage Crypto', totalPnL: -3200.00, winRate: 72, sharpeRatio: -0.3, maxDrawdown: -5.1 },
    { strategy: 'Mean Reversion Stocks', totalPnL: 18750.00, winRate: 62, sharpeRatio: 1.2, maxDrawdown: -10.0 },
  ];

  const getStatusIcon = (status) => {
    switch (status) {
      case 'Active':
        return faPlay;
      case 'Paused':
        return faPause;
      case 'Error':
        return faExclamationTriangle;
      default:
        return faStop;
    }
  };

  const getStatusBadgeColor = (status, statusColor) => {
    if (statusColor === 'green') {
      return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300';
    }
    if (statusColor === 'orange') {
      return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300';
    }
    if (statusColor === 'red') {
      return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
    }
    return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300';
  };

  const getConfidenceColor = (confidence) => {
    switch (confidence) {
      case 'High':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300';
      case 'Medium':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300';
      case 'Low':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300';
    }
  };

  const getSignalStatusColor = (status) => {
    switch (status) {
      case 'Executed':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300';
      case 'Pending':
        return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300';
      case 'Rejected':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300';
    }
  };

  const handleCloseAllPositions = () => {
    if (window.confirm('Are you sure you want to close all positions? This action cannot be undone.')) {
      // TODO: Implement close all positions
      console.log('Closing all positions...');
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Strategy Settings</h1>
      </div>

      {/* Emergency Controls */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Emergency Controls</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Global settings to manage all active strategies and positions.
        </p>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Master Switch (ON/OFF)
              </label>
            </div>
            <button
              onClick={() => setMasterSwitch(!masterSwitch)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                masterSwitch ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  masterSwitch ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Pause All Strategies
              </label>
            </div>
            <button
              onClick={() => setPauseAllStrategies(!pauseAllStrategies)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                pauseAllStrategies ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  pauseAllStrategies ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Close All Positions
              </label>
            </div>
            <button
              onClick={() => setCloseAllPositions(!closeAllPositions)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                closeAllPositions ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  closeAllPositions ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div className="pt-2">
            <button
              onClick={handleCloseAllPositions}
              className="text-sm text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 font-medium transition-colors"
            >
              Close All Positions
            </button>
          </div>
        </div>
      </div>

      {/* My Trading Strategies */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">My Trading Strategies</h2>
          <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2">
            <FontAwesomeIcon icon={faPlus} />
            Add New Strategy
          </button>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
          {strategies.map((strategy) => (
            <div key={strategy.id} className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">{strategy.name}</h3>
                  <div className="flex items-center gap-2 mb-2">
                    <FontAwesomeIcon 
                      icon={getStatusIcon(strategy.status)} 
                      className={`text-xs ${
                        strategy.statusColor === 'green' ? 'text-green-600 dark:text-green-400' :
                        strategy.statusColor === 'orange' ? 'text-orange-600 dark:text-orange-400' :
                        'text-red-600 dark:text-red-400'
                      }`}
                    />
                    <span className={`text-sm font-medium ${getStatusBadgeColor(strategy.status, strategy.statusColor)} px-2.5 py-0.5 rounded-full`}>
                      {strategy.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    <FontAwesomeIcon icon={faEye} />
                  </button>
                  <button className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                    <FontAwesomeIcon icon={faEdit} />
                  </button>
                </div>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{strategy.description}</p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-600 dark:text-gray-400">Daily P&L:</span>
                  <span className={`text-sm font-medium ${
                    strategy.dailyPnLColor === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {strategy.dailyPnL >= 0 ? '+' : ''}{strategy.dailyPnL}%
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-600 dark:text-gray-400">Win Rate:</span>
                  <span className="text-sm font-medium text-gray-900 dark:text-white">{strategy.winRate}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-600 dark:text-gray-400">Max Drawdown:</span>
                  <span className="text-sm font-medium text-red-600 dark:text-red-400">{strategy.maxDrawdown}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Strategy Signals Monitor */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Strategy Signals Monitor</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">Real-time feed of signals generated by active strategies.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Timestamp</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Strategy</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Direction</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Confidence</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {strategySignals.map((signal, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{signal.timestamp}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{signal.strategy}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{signal.symbol}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      signal.direction === 'Buy'
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                    }`}>
                      {signal.direction}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getConfidenceColor(signal.confidence)}`}>
                      {signal.confidence}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSignalStatusColor(signal.status)}`}>
                      {signal.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Strategy Performance Comparison */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Strategy Performance Comparison</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">Evaluate the performance of different strategies over time.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Strategy</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Total P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Win Rate</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Sharpe Ratio</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Max Drawdown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {performanceComparison.map((strategy, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{strategy.strategy}</td>
                  <td className={`px-6 py-4 text-sm font-medium ${
                    strategy.totalPnL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {strategy.totalPnL >= 0 ? '+' : ''}${strategy.totalPnL.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{strategy.winRate}%</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{strategy.sharpeRatio}</td>
                  <td className="px-6 py-4 text-sm font-medium text-red-600 dark:text-red-400">{strategy.maxDrawdown}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
