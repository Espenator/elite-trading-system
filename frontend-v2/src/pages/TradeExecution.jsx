import React, { useState } from 'react';

const TradeExecution = () => {
  const [symbol, setSymbol] = useState('TSLA');
  const [orderType, setOrderType] = useState('Limit');
  const [quantity, setQuantity] = useState(100);
  const [price, setPrice] = useState(150.25);
  const [timeframe, setTimeframe] = useState('1D');

  const estimatedCost = quantity * price;
  const requiredMargin = estimatedCost * 0.5;
  const potentialPL = 250.00;
  const riskStatus = 'Within Limits';

  const handleBuy = () => {
    console.log('Buy order placed:', { symbol, orderType, quantity, price });
  };

  const handleSell = () => {
    console.log('Sell order placed:', { symbol, orderType, quantity, price });
  };

  return (
    <div className="min-h-screen bg-dark text-white p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Trade Execution</h1>
        <p className="text-secondary">Execute and manage trades with real-time data and risk validation.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart Section */}
        <div className="lg:col-span-2">
          <div className="bg-secondary/10 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{symbol} Chart</h2>
              <div className="flex gap-2">
                <button onClick={() => setTimeframe('15M')} className={`px-3 py-1 rounded ${timeframe === '15M' ? 'bg-primary' : 'bg-secondary/50'}`}>15M</button>
                <button onClick={() => setTimeframe('1H')} className={`px-3 py-1 rounded ${timeframe === '1H' ? 'bg-primary' : 'bg-secondary/50'}`}>1H</button>
                <button onClick={() => setTimeframe('4H')} className={`px-3 py-1 rounded ${timeframe === '4H' ? 'bg-primary' : 'bg-secondary/50'}`}>4H</button>
                <button onClick={() => setTimeframe('1D')} className={`px-3 py-1 rounded ${timeframe === '1D' ? 'bg-primary' : 'bg-secondary/50'}`}>1D</button>
              </div>
            </div>
            <div className="h-96 flex items-center justify-center bg-dark rounded">
              <p className="text-secondary">Interactive Chart for {symbol}</p>
            </div>
          </div>
        </div>

        {/* Order Entry Section */}
        <div className="space-y-6">
          <div className="bg-secondary/10 rounded-lg p-6">
            <h2 className="text-xl font-bold mb-4">Order Entry for {symbol}</h2>
            
            {/* Order Type */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Order Type</label>
              <select 
                value={orderType} 
                onChange={(e) => setOrderType(e.target.value)}
                className="w-full bg-secondary/50 border border-secondary/50 rounded px-3 py-2"
              >
                <option value="Limit">Limit</option>
                <option value="Market">Market</option>
                <option value="Stop">Stop</option>
                <option value="Stop Limit">Stop Limit</option>
              </select>
            </div>

            {/* Quantity */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Quantity</label>
              <input 
                type="number" 
                value={quantity}
                onChange={(e) => setQuantity(parseFloat(e.target.value))}
                className="w-full bg-secondary/50 border border-secondary/50 rounded px-3 py-2"
              />
            </div>

            {/* Price */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Price</label>
              <input 
                type="number" 
                value={price}
                onChange={(e) => setPrice(parseFloat(e.target.value))}
                step="0.01"
                className="w-full bg-secondary/50 border border-secondary/50 rounded px-3 py-2"
              />
            </div>

            {/* Buy/Sell Buttons */}
            <div className="flex gap-3">
              <button 
                onClick={handleBuy}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white font-semibold py-3 rounded flex items-center justify-center gap-2"
              >
                <span>↗</span> Buy
              </button>
              <button 
                onClick={handleSell}
                className="flex-1 bg-red-600 hover:bg-red-700 text-white font-semibold py-3 rounded flex items-center justify-center gap-2"
              >
                <span>↙</span> Sell
              </button>
            </div>
          </div>

          {/* Order Preview */}
          <div className="bg-secondary/10 rounded-lg p-6">
            <h3 className="text-lg font-bold mb-4">Order Preview</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-secondary">Estimated Cost:</span>
                <span className="font-semibold">${estimatedCost.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Required Margin:</span>
                <span className="font-semibold">${requiredMargin.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-secondary">Potential P&L:</span>
                <span className="font-semibold text-green-500">+ ${potentialPL.toLocaleString()}</span>
              </div>
              <div className="pt-3 border-t border-secondary/50">
                <div className="flex justify-between items-center">
                  <span className="text-secondary">Risk Status:</span>
                  <span className="font-semibold text-green-500">{riskStatus}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradeExecution;
