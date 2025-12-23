import { useState } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faChartLine, faArrowUp, faArrowDown } from '@fortawesome/free-solid-svg-icons';
import { ChartArea } from '../components/ChartArea';

export default function TradeExecution() {
  const [selectedSymbol, setSelectedSymbol] = useState('TSLA');
  const [orderType, setOrderType] = useState('Limit');
  const [orderSide, setOrderSide] = useState('buy');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState(150.25);

  const recentOrders = [
    { time: '10:30:15', symbol: 'TSLA', side: 'Buy', qty: 100, price: 150.25, status: 'Filled' },
    { time: '10:25:01', symbol: 'MSFT', side: 'Sell', qty: 50, price: 410.50, status: 'Filled' },
    { time: '10:20:30', symbol: 'GOOG', side: 'Buy', qty: 20, price: 175.80, status: 'Pending' },
    { time: '10:15:45', symbol: 'AAPL', side: 'Stop', qty: 150, price: 170.00, status: 'Filled' },
    { time: '10:10:00', symbol: 'AMZN', side: 'Buy', qty: 30, price: 185.10, status: 'Filled' },
  ];

  const executionLogs = [
    { timestamp: '2023-10-27 10:30:15', symbol: 'TSLA', type: 'Limit', side: 'Buy', qty: 100, price: 150.25, filled: 100, status: 'Filled' },
    { timestamp: '2023-10-27 10:25:01', symbol: 'MSFT', type: 'Limit', side: 'Sell', qty: 50, price: 410.50, filled: 50, status: 'Filled' },
    { timestamp: '2023-10-27 10:20:30', symbol: 'GOOG', type: 'Limit', side: 'Buy', qty: 20, price: 175.80, filled: 0, status: 'Pending' },
    { timestamp: '2023-10-27 10:15:45', symbol: 'AAPL', type: 'Stop', side: 'Sell', qty: 150, price: 170.00, filled: 150, status: 'Filled' },
    { timestamp: '2023-10-27 10:10:00', symbol: 'AMZN', type: 'Limit', side: 'Buy', qty: 30, price: 185.10, filled: 30, status: 'Filled' },
    { timestamp: '2023-10-27 09:55:20', symbol: 'NVDA', type: 'Market', side: 'Buy', qty: 10, price: 480.00, filled: 10, status: 'Filled' },
    { timestamp: '2023-10-27 09:45:10', symbol: 'AMD', type: 'Limit', side: 'Buy', qty: 200, price: 105.50, filled: 0, status: 'Cancelled' },
    { timestamp: '2023-10-27 09:30:05', symbol: 'NFLX', type: 'Market', side: 'Buy', qty: 5, price: 400.00, filled: 5, status: 'Filled' },
  ];

  const estimatedCost = quantity * price;
  const requiredMargin = estimatedCost * 0.5;
  const potentialPnL = estimatedCost * 0.02;

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Trade Execution</h1>
        <p className="text-gray-600 dark:text-gray-400 mt-1">Execute and manage trades with real-time data and risk validation.</p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Section - Takes 2 columns */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{selectedSymbol} Chart</h2>
              </div>
            <div className="h-96">
              <ChartArea selectedSignal={{ symbol: selectedSymbol }} />
            </div>
          </div>
        </div>

        {/* Order Entry Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Order Entry for {selectedSymbol}</h2>
          </div>
          <div className="p-6 space-y-4">
            {/* Order Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Order Type</label>
              <select 
                value={orderType}
                onChange={(e) => setOrderType(e.target.value)}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              >
                <option>Limit</option>
                <option>Market</option>
                <option>Stop</option>
                <option>Stop Limit</option>
              </select>
            </div>

            {/* Quantity */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Quantity</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Number(e.target.value))}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Price</label>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(Number(e.target.value))}
                step="0.01"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Buy/Sell Buttons */}
            <div className="flex space-x-3">
              <button 
                onClick={() => setOrderSide('buy')}
                className="flex-1 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
              >
                <FontAwesomeIcon icon={faArrowUp} className="mr-2" />
                Buy
              </button>
              <button 
                onClick={() => setOrderSide('sell')}
                className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
              >
                <FontAwesomeIcon icon={faArrowDown} className="mr-2" />
                Sell
              </button>
            </div>

            {/* Order Preview */}
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Order Preview</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Estimated Cost:</span>
                  <span className="font-medium text-gray-900 dark:text-white">${estimatedCost.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Required Margin:</span>
                  <span className="font-medium text-gray-900 dark:text-white">${requiredMargin.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Potential P&L:</span>
                  <span className="font-medium text-green-600">+ ${potentialPnL.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">Risk Status:</span>
                  <span className="font-medium text-green-600">Within Limits</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Orders */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Orders</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Time</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Side</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Qty</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {recentOrders.map((order, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.time}</td>
                  <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{order.symbol}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={order.side === 'Buy' ? 'text-green-600' : 'text-red-600'}>
                      {order.side}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.qty}</td>
                  <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">${order.price}</td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      order.status === 'Filled' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                      'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300'
                    }`}>
                      {order.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ML Insights & Advanced Settings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ML Insights */}
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg border border-purple-200 dark:border-purple-800 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">ML Insights for {selectedSymbol}</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-gray-700 dark:text-gray-300">Sentiment:</span>
              <span className="font-medium text-blue-600 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 rounded">Bullish</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-700 dark:text-gray-300">Confidence:</span>
              <span className="font-medium text-gray-900 dark:text-white">85%</span>
            </div>
            <div className="mt-4 pt-4 border-t border-purple-200 dark:border-purple-700">
              <p className="text-sm text-gray-700 dark:text-gray-300">Price increase expected in next 4 hours.</p>
            </div>
          </div>
        </div>

        {/* Advanced Order Settings */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Advanced Order Settings</h3>
          <div className="space-y-4">
            {/* Bracket Orders */}
            <div>
              <button className="w-full flex items-center justify-between px-4 py-2 text-left bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm font-medium text-gray-900 dark:text-white">Bracket Orders (OCO)</span>
                <span className="text-gray-400">▼</span>
              </button>
            </div>

            {/* Trailing Stop */}
            <div>
              <button className="w-full flex items-center justify-between px-4 py-2 text-left bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm font-medium text-gray-900 dark:text-white">Trailing Stop</span>
                <span className="text-gray-400">▼</span>
              </button>
            </div>

            {/* Time in Force */}
            <div>
              <button className="w-full flex items-center justify-between px-4 py-2 text-left bg-gray-50 dark:bg-gray-900 rounded-lg">
                <span className="text-sm font-medium text-gray-900 dark:text-white">Time in Force</span>
                <span className="text-gray-400">▼</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Execution Logs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Detailed Execution Logs</h2>
          <button className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-600">
            Apply Filters
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-900/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Timestamp</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Symbol</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Side</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Qty</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Price</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Filled Qty</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {executionLogs.map((log, index) => (
                <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400">{log.timestamp}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{log.symbol}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{log.type}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={log.side === 'Buy' ? 'text-green-600' : 'text-red-600'}>
                      {log.side}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{log.qty}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">${log.price}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{log.filled}</td>
                  <td className="px-4 py-3 text-sm">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      log.status === 'Filled' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                      log.status === 'Pending' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                      'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
                    }`}>
                      {log.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

