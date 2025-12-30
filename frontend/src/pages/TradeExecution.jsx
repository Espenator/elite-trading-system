import { useState, useEffect } from 'react';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faArrowUp, faArrowDown } from '@fortawesome/free-solid-svg-icons';
import { ChartArea } from '../components/ChartArea';
import tradeService from '../services/trade.service';

export default function TradeExecution() {
  const [selectedSymbol, setSelectedSymbol] = useState('TSLA');
  const [orderType, setOrderType] = useState('Limit');
  const [orderSide, setOrderSide] = useState('buy');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState(150.25);
  const [stockList, setStockList] = useState([]);
  const [isLoadingStocks, setIsLoadingStocks] = useState(true);
  const [recentOrders, setRecentOrders] = useState([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);
  const [isSubmittingOrder, setIsSubmittingOrder] = useState(false);

  // Fetch stock list on mount
  useEffect(() => {
    const fetchStocks = async () => {
      try {
        setIsLoadingStocks(true);
        const stocks = await tradeService.getStockList();
        setStockList(stocks);
        
        // Set default symbol if available
        if (stocks && stocks.length > 0 && !selectedSymbol) {
          setSelectedSymbol(stocks[0].Ticker || 'TSLA');
        }
      } catch (error) {
        console.error('Error fetching stock list:', error);
      } finally {
        setIsLoadingStocks(false);
      }
    };

    fetchStocks();
  }, []);

  // Fetch recent orders on mount and when orders change
  useEffect(() => {
    const fetchRecentOrders = async () => {
      try {
        setIsLoadingOrders(true);
        const orders = await tradeService.getRecentOrders(10);
        setRecentOrders(orders);
      } catch (error) {
        console.error('Error fetching recent orders:', error);
        setRecentOrders([]);
      } finally {
        setIsLoadingOrders(false);
      }
    };

    fetchRecentOrders();
  }, []);

  // Update price when symbol changes (you can enhance this to fetch real-time price)
  useEffect(() => {
    if (selectedSymbol && stockList.length > 0) {
      const stock = stockList.find(s => s.Ticker === selectedSymbol);
      if (stock && stock.Price) {
        const priceValue = parseFloat(stock.Price.toString().replace(/[^0-9.-]/g, '') || '0');
        if (priceValue > 0) {
          setPrice(priceValue);
        }
      }
    }
  }, [selectedSymbol, stockList]);

  const estimatedCost = quantity * price;
  const requiredMargin = estimatedCost * 0.5;
  const potentialPnL = estimatedCost * 0.02;

  // Handle order submission
  const handleSubmitOrder = async (side = null) => {
    const orderSideToUse = side || orderSide;
    
    if (!selectedSymbol || quantity <= 0 || price <= 0) {
      alert('Please fill in all required fields with valid values');
      return;
    }

    try {
      setIsSubmittingOrder(true);
      const orderData = {
        symbol: selectedSymbol,
        order_type: orderType,
        side: orderSideToUse,
        quantity: quantity,
        price: price,
        estimated_cost: estimatedCost,
        required_margin: requiredMargin,
        potential_pnl: potentialPnL
      };

      await tradeService.createOrder(orderData);
      
      // Refresh recent orders
      const orders = await tradeService.getRecentOrders(10);
      setRecentOrders(orders);
      
      alert(`Order placed successfully! ${orderSideToUse === 'buy' ? 'Buy' : 'Sell'} ${quantity} shares of ${selectedSymbol} at $${price.toFixed(2)}`);
    } catch (error) {
      console.error('Error submitting order:', error);
      alert('Failed to place order. Please try again.');
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  // Format time from ISO string to HH:MM:SS
  const formatTime = (isoString) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch (error) {
      return isoString;
    }
  };

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
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">              
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Select Ticker:</label>
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  disabled={isLoadingStocks}
                  className="px-3 py-2 bg-gray-50 dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 min-w-[150px] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingStocks ? (
                    <option>Loading...</option>
                  ) : stockList.length > 0 ? (
                    stockList.map((stock) => (
                      <option key={stock.Ticker} value={stock.Ticker}>
                        {stock.Ticker} - {stock.Company}
                      </option>
                    ))
                  ) : (
                    <option value="TSLA">TSLA - Tesla Inc</option>
                  )}
                </select>
              </div>
            </div>
            <div className="h-[550px]">
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
                onClick={() => {
                  setOrderSide('buy');
                  handleSubmitOrder('buy');
                }}
                disabled={isSubmittingOrder}
                className={`flex-1 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors ${
                  orderSide === 'buy' ? 'ring-2 ring-green-400' : ''
                } ${isSubmittingOrder ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <FontAwesomeIcon icon={faArrowUp} className="mr-2" />
                {isSubmittingOrder && orderSide === 'buy' ? 'Submitting...' : 'Buy'}
              </button>
              <button 
                onClick={() => {
                  setOrderSide('sell');
                  handleSubmitOrder('sell');
                }}
                disabled={isSubmittingOrder}
                className={`flex-1 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors ${
                  orderSide === 'sell' ? 'ring-2 ring-red-400' : ''
                } ${isSubmittingOrder ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <FontAwesomeIcon icon={faArrowDown} className="mr-2" />
                {isSubmittingOrder && orderSide === 'sell' ? 'Submitting...' : 'Sell'}
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
              {isLoadingOrders ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    Loading orders...
                  </td>
                </tr>
              ) : recentOrders.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                    No orders yet. Place your first order above!
                  </td>
                </tr>
              ) : (
                recentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                      {formatTime(order.created_at)}
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">{order.symbol}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={order.side === 'buy' || order.side === 'Buy' ? 'text-green-600' : 'text-red-600'}>
                        {order.side === 'buy' ? 'Buy' : 'Sell'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">{order.quantity}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">${parseFloat(order.price).toFixed(2)}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        order.status === 'Filled' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                        order.status === 'Pending' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                        'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
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
              {isLoadingOrders ? (
                <tr>
                  <td colSpan="8" className="px-4 py-3 text-center text-sm text-gray-500 dark:text-gray-400">
                    Loading execution logs...
                  </td>
                </tr>
              ) : recentOrders.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-4 py-3 text-center text-sm text-gray-500 dark:text-gray-400">
                    No execution logs available.
                  </td>
                </tr>
              ) : (
                recentOrders.map((log) => (
                  <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                    <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{log.symbol}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{log.order_type}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={log.side === 'buy' || log.side === 'Buy' ? 'text-green-600' : 'text-red-600'}>
                        {log.side === 'buy' ? 'Buy' : 'Sell'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">{log.quantity}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">${parseFloat(log.price).toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                      {log.status === 'Filled' ? log.quantity : 0}
                    </td>
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
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

