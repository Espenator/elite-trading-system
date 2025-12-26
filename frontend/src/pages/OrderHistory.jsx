import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { 
  faHistory, faDownload, faShare, faEye, faPlay,
  faChartLine, faChartBar, faBalanceScale
} from '@fortawesome/free-solid-svg-icons';

export default function OrderHistory() {
  const [strategy, setStrategy] = useState('Mean Reversion Algo v2.1');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
  const [initialCapital, setInitialCapital] = useState(100000);
  const [commission, setCommission] = useState(0.001);
  const [riskTolerance, setRiskTolerance] = useState(75);

  // Executed Orders Data
  const executedOrders = [
    { orderId: 'TS-89376', symbol: 'NVDA', type: 'BUY', qty: 100, price: 915.20, status: 'FILLED', date: '2024-01-15 14:30:22', pnl: 1250.75, pnlColor: 'green' },
    { orderId: 'TS-89375', symbol: 'MSFT', type: 'SELL', qty: 150, price: 420.10, status: 'FILLED', date: '2024-01-15 13:45:18', pnl: 890.00, pnlColor: 'green' },
    { orderId: 'TS-89374', symbol: 'GOOGL', type: 'BUY', qty: 200, price: 155.00, status: 'FILLED', date: '2024-01-15 12:20:05', pnl: -300.20, pnlColor: 'red' },
    { orderId: 'TS-89373', symbol: 'AMZN', type: 'BUY', qty: 80, price: 180.30, status: 'FILLED', date: '2024-01-15 11:15:42', pnl: 2100.50, pnlColor: 'green' },
    { orderId: 'TS-89372', symbol: 'AAPL', type: 'SELL', qty: 120, price: 172.55, status: 'FILLED', date: '2024-01-15 10:05:30', pnl: 700.00, pnlColor: 'green' },
    { orderId: 'TS-89371', symbol: 'TSLA', type: 'BUY', qty: 90, price: 189.50, status: 'FILLED', date: '2024-01-15 09:30:15', pnl: -550.00, pnlColor: 'red' },
  ];

  // Backtest Performance Summary
  const performanceMetrics = [
    { label: 'Net Profit', value: '$12,500.78', change: '+15.2%', trend: 'up', color: 'green' },
    { label: 'Sharpe Ratio', value: '1.85', change: '+0.03', trend: 'up', color: 'green', icon: faChartLine },
    { label: 'Max Drawdown', value: '-8.12%', change: '+0.5%', trend: 'up', color: 'green', icon: faChartBar },
    { label: 'Win Rate', value: '62.5%', change: '+1.2%', trend: 'up', color: 'green', icon: faBalanceScale },
  ];

  // Trade Distribution Data
  const tradeDistribution = [
    { label: 'Wins', count: 125, total: 200, color: 'bg-blue-600' },
    { label: 'Losses', count: 60, total: 200, color: 'bg-pink-500' },
    { label: 'Breakeven', count: 15, total: 200, color: 'bg-teal-500' },
  ];

  // Monthly Returns Heatmap Data (simplified - showing sample data)
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const daysInMonth = [5, 10, 15, 20, 25, 30];
  
  // Sample daily returns data (simplified representation)
  const getDailyReturn = (month, day) => {
    // Generate sample data - in real implementation, this would come from API
    if (month === 0 && [5, 10, 15, 20, 25, 30].includes(day)) {
      const values = [-1, 0, 1, 2, 9];
      return values[Math.floor(Math.random() * values.length)];
    }
    if (month === 1 && [5, 10, 15].includes(day)) {
      return Math.floor(Math.random() * 5) - 2;
    }
    return null; // No data for other days
  };

  const getReturnColor = (value) => {
    if (value === null) return 'bg-gray-100 dark:bg-gray-700';
    if (value > 5) return 'bg-green-600 dark:bg-green-700';
    if (value > 2) return 'bg-green-400 dark:bg-green-600';
    if (value > 0) return 'bg-green-200 dark:bg-green-500';
    if (value === 0) return 'bg-gray-200 dark:bg-gray-600';
    if (value > -2) return 'bg-red-200 dark:bg-red-500';
    return 'bg-red-400 dark:bg-red-600';
  };

  const handleReset = () => {
    setStrategy('Mean Reversion Algo v2.1');
    setStartDate('2023-01-01');
    setEndDate('2023-12-31');
    setInitialCapital(100000);
    setCommission(0.001);
    setRiskTolerance(75);
  };

  const handleRunBacktest = () => {
    // TODO: Implement backtest execution
    console.log('Running backtest with:', { strategy, startDate, endDate, initialCapital, commission, riskTolerance });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Order History & Backtest</h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Review past trade executions and evaluate strategy performance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <FontAwesomeIcon icon={faDownload} className="text-xl" />
          </button>
          <button className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
            <FontAwesomeIcon icon={faShare} className="text-xl" />
          </button>
        </div>
      </div>

      {/* Executed Orders Section */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Executed Orders</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">Detailed log of all trades executed by the system.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Order ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Qty</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">P&L</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {executedOrders.map((order, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{order.orderId}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.symbol}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      order.type === 'BUY' 
                        ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                        : 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                    }`}>
                      {order.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.qty}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">${order.price.toFixed(2)}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                      {order.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.date}</td>
                  <td className={`px-6 py-4 text-sm font-medium ${
                    order.pnlColor === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                  }`}>
                    {order.pnl >= 0 ? '+' : ''}${order.pnl.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">
                      <FontAwesomeIcon icon={faEye} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Backtest Configuration and Performance Summary Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Backtest Configuration */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Backtest Configuration</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Set parameters to simulate strategy performance over historical data.
          </p>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Strategy</label>
              <input
                type="text"
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Start Date</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">End Date</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Initial Capital ($)</label>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Commission (%)</label>
                <input
                  type="number"
                  step="0.001"
                  value={commission}
                  onChange={(e) => setCommission(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Risk Tolerance: {riskTolerance}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={riskTolerance}
                onChange={(e) => setRiskTolerance(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors"
              >
                Reset
              </button>
              <button
                onClick={handleRunBacktest}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
              >
                <FontAwesomeIcon icon={faPlay} />
                Run Backtest
              </button>
            </div>
          </div>
        </div>

        {/* Backtest Performance Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Backtest Performance Summary</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Key metrics from the latest backtest run.
          </p>
          <div className="space-y-4">
            {performanceMetrics.map((metric, index) => (
              <div key={index} className="bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {metric.icon && (
                      <FontAwesomeIcon icon={metric.icon} className="text-gray-400 dark:text-gray-500 text-sm" />
                    )}
                    <span className="text-sm text-gray-600 dark:text-gray-400">{metric.label}</span>
                  </div>
                </div>
                <div className="text-xl font-bold text-gray-900 dark:text-white mb-1">{metric.value}</div>
                <div className={`text-sm font-medium ${
                  metric.color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                }`}>
                  {metric.change}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trade Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Trade Distribution</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Overview of winning, losing, and breakeven trades.
        </p>
        <div className="space-y-3">
          {tradeDistribution.map((item, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className="w-24 text-sm text-gray-600 dark:text-gray-400">{item.label}</div>
              <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-8 relative">
                <div
                  className={`${item.color} h-8 rounded-full flex items-center justify-end pr-3 text-white text-sm font-medium`}
                  style={{ width: `${(item.count / item.total) * 100}%` }}
                >
                  {item.count}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Monthly Returns Heatmap */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Monthly Returns Heatmap</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
          Daily return performance across the trading year.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="px-2 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 text-left">Month</th>
                {daysInMonth.map(day => (
                  <th key={day} className="px-1 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 text-center min-w-[30px]">
                    {day}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {months.map((month, monthIdx) => (
                <tr key={month}>
                  <td className="px-2 py-2 text-sm font-medium text-gray-900 dark:text-white">{month}</td>
                  {daysInMonth.map(day => {
                    const value = getDailyReturn(monthIdx, day);
                    return (
                      <td key={day} className="px-1 py-1">
                        <div className={`w-6 h-6 rounded ${getReturnColor(value)} flex items-center justify-center text-xs font-medium ${
                          value !== null ? 'text-white' : 'text-gray-400 dark:text-gray-500'
                        }`}>
                          {value !== null ? value : ''}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
